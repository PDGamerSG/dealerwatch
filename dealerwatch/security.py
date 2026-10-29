"""Optional local operator authentication, same-origin writes and bounded request bodies."""
from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

COOKIE = "dw_session"
SESSION_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class Principal:
    role: str
    reviewer: str | None
    authenticated: bool


class Security:
    """Configured tokens stay server-side; browser sessions use opaque expiring cookies."""

    def __init__(self):
        self.admin = os.environ.get("DW_ADMIN_TOKEN", "").strip()
        self.reviewer = os.environ.get("DW_REVIEWER_TOKEN", "").strip()
        if self.admin and self.admin == self.reviewer:
            raise ValueError("Admin and reviewer tokens must be different")
        self.required = bool(self.admin or self.reviewer)
        self.sessions: dict[str, tuple[float, Principal]] = {}
        self.attempts: dict[str, list[float]] = {}
        self.lock = threading.RLock()

    def token_principal(self, token: str) -> Principal | None:
        if self.admin and hmac.compare_digest(token.encode(), self.admin.encode()):
            return Principal("admin", os.environ.get("DW_ADMIN_NAME", "Administrator"), True)
        if self.reviewer and hmac.compare_digest(token.encode(), self.reviewer.encode()):
            return Principal("reviewer", os.environ.get("DW_REVIEWER_NAME", "Compliance Reviewer"), True)
        return None

    def principal(self, request: Request) -> Principal | None:
        if not self.required:
            return Principal("admin", None, False)
        authorization = request.headers.get("Authorization", "")
        if authorization:
            scheme, _, value = authorization.partition(" ")
            return self.token_principal(value) if scheme.lower() == "bearer" else None
        session_id = request.cookies.get(COOKIE, "")
        with self.lock:
            value = self.sessions.get(session_id)
            if value and value[0] > time.monotonic():
                return value[1]
            self.sessions.pop(session_id, None)
        return None

    def require(self, request: Request, role: str | None = None) -> Principal:
        principal = self.principal(request)
        if principal is None:
            raise HTTPException(401, "Sign in to access investigations", headers={"WWW-Authenticate": "Bearer"})
        if role == "admin" and principal.role != "admin":
            raise HTTPException(403, "Administrator access is required")
        return principal

    def status(self, request: Request) -> dict:
        principal = self.principal(request)
        return {"auth_required": self.required, "authenticated": bool(principal and principal.authenticated),
                "role": principal.role if principal else None, "reviewer": principal.reviewer if principal else None,
                "demo_enabled": os.environ.get("DW_DEMO", "0") == "1"}

    def login(self, request: Request, token: str) -> tuple[str, Principal]:
        client = request.client.host if request.client else "unknown"
        tick = time.monotonic()
        with self.lock:
            # Bound both memory and failed attempts, without logging tokens.
            self.attempts = {key: [t for t in values if tick - t < 60] for key, values in self.attempts.items()
                             if values and tick - values[-1] < 60}
            if len(self.attempts) > 10000:
                raise HTTPException(429, "Too many authentication attempts; retry shortly")
            attempts = self.attempts.setdefault(client, [])
            if len(attempts) >= 10:
                raise HTTPException(429, "Too many authentication attempts; retry in one minute")
            attempts.append(tick)
            principal = self.token_principal(token)
            if not principal:
                raise HTTPException(401, "Invalid access token")
            self.attempts.pop(client, None)
            self.sessions = {key: value for key, value in self.sessions.items() if value[0] > tick}
            if len(self.sessions) >= 10000:
                raise HTTPException(429, "Session capacity reached")
            session_id = secrets.token_urlsafe(32)
            self.sessions[session_id] = (tick + SESSION_SECONDS, principal)
        return session_id, principal

    def logout(self, request: Request) -> None:
        with self.lock:
            self.sessions.pop(request.cookies.get(COOKIE, ""), None)


class RequestLimits:
    """Pure ASGI middleware: bounds streamed bodies before JSON parsing, including chunked input."""

    def __init__(self, app, max_bytes: int = 32 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
        request_id = uuid.uuid4().hex

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), (b"x-request-id", request_id.encode())]
            await send(message)

        async def reject(code, detail):
            response = JSONResponse({"detail": detail, "request_id": request_id}, status_code=code,
                                    headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})
            await response(scope, receive, send_with_id)

        # Evaluation can compute/cache on GET for the original API contract, so guard it like a write.
        if scope["method"] not in {"GET", "HEAD", "OPTIONS"} or scope.get("path") == "/api/eval":
            origin = headers.get("origin")
            if origin:
                parsed = urlsplit(origin)
                expected = (scope.get("scheme", "http"), headers.get("host", ""))
                if (parsed.scheme, parsed.netloc) != expected or parsed.path not in ("", "/"):
                    return await reject(403, "Cross-origin mutations are not allowed")
            if headers.get("sec-fetch-site") == "cross-site":
                return await reject(403, "Cross-site mutations are not allowed")
        try:
            if int(headers.get("content-length", "0")) > self.max_bytes:
                return await reject(413, "Request body exceeds the configured upload limit")
        except ValueError:
            return await reject(400, "Invalid Content-Length")
        parts, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            part = message.get("body", b"")
            size += len(part)
            if size > self.max_bytes:
                return await reject(413, "Request body exceeds the configured upload limit")
            parts.append(part)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(parts), "more_body": False}
            return await receive()

        scope.setdefault("state", {})["request_id"] = request_id
        await self.app(scope, replay, send_with_id)
