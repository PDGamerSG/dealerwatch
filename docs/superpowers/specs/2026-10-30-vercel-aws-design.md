# Vercel frontend and AWS backend deployment

The user explicitly requested publication and end-to-end live testing, then selected Vercel for the frontend and AWS for the backend. Keep the verified FastAPI/SQLite investigation workflow and basic frontend. This is deployment work; the existing case, audit and decision semantics remain authoritative.

## Hosting

Vercel serves only the three web assets and proxies `/api/*` and `/audio/*` over HTTPS to AWS. The Build Output API configuration is generated from `DW_BACKEND_URL`; builds reject insecure origins or credentials in URLs. Frontend requests remain same-origin, avoiding cross-domain cookies and CORS configuration. API and evidence responses must never be cached by the CDN.

Run one backend container on an Ubuntu 24.04 AWS Lightsail instance in Mumbai (`ap-south-1`), with a static public IPv4 address. The intended 2 GB plan costs $12/month before any applicable credits, taxes or additional usage. Verify the current account and bundle price before creating the instance. Bind the full `/data` directory to `/srv/dealerwatch/data` on the persistent instance disk and retain rollback-journal SQLite. No case databases reside on Vercel's temporary filesystem or a network filesystem.

Caddy terminates HTTPS using Let's Encrypt public-IP certificates with the `shortlived` ACME profile. Pin the Caddy release and persist its certificate state. Configure `default_sni` to the static public IP for clients that do not send an IP in SNI. Application port 8077 is accessible only inside Docker and through host loopback. Expose only ports 80 and 443 publicly and restrict SSH to the operator IP. Stopping/restarting or rebuilding the application preserves the data; deleting the AWS instance requires a backup first.

## Security and configuration

Require distinct administrator and reviewer tokens for the hosted backend. Store runtime secrets outside Git, outside Vercel's static output and outside the Docker build context. Use secure HttpOnly session cookies. `DW_PUBLIC_ORIGINS` is an exact HTTPS allowlist for the Vercel URL; never trust arbitrary forwarded-host values or wildcard domains. Public same-origin mutations through Vercel must pass, while foreign origins and cross-site requests must fail.

Do not auto-accept an AWS paid plan upgrade. Existing AWS CLI session reauthentication is required before creating resources. The Vercel project is `dealerwatch` under the authenticated team. Deploy a preview unless the user explicitly asks for a production deployment.

## Live acceptance

1. Fresh container startup seeds and investigates 19 expected synthetic cases; readiness, dashboard, queue, detail and static assets respond through Vercel.
2. Administrator and reviewer browser sessions work through HTTPS, role restrictions remain enforced, and foreign-origin writes fail.
3. The full desktop and mobile workflows pass against a disposable synthetic deployment, explicitly opting into demo reset: review, request information, escalation, dismissal, filters, data validation/import/export, background runs, audit tamper/restore, evaluation links and evidence downloads.
4. Read-only deployment checks verify all cases, evidence SHA-256, audit integrity, CSV/dataset exports, evaluation links and asset responses without exposing credentials.
5. A case review, imported data and completed run survive a backend container restart/recreation with a valid ledger. Audio served from archived evidence remains accessible when synthetic recordings are installed.
6. Finish with demo mutations disabled, the final URL, commit, measured results and any external provider limitations. Do not report live success before testing the actual deployment.
