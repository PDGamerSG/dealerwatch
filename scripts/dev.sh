#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' >&2
  exit 1
fi
if [ -f .env ]; then
  exec uv run --frozen --env-file .env python -m dealerwatch "$@"
fi
exec uv run --frozen python -m dealerwatch "$@"
