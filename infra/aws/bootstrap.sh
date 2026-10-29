#!/usr/bin/env bash
# Run on an Ubuntu 24.04 AWS VM, after attaching its static IPv4 address:
#   sudo bash infra/aws/bootstrap.sh /srv/dealerwatch/aws.env
# Keep the environment file outside this checkout, with these keys:
#   PUBLIC_IP, DW_ADMIN_TOKEN, DW_REVIEWER_TOKEN, DW_PUBLIC_ORIGINS
# DW_PUBLIC_ORIGINS is a comma-separated list of exact HTTPS origins.
# DW_DEMO defaults to 0. TCP 80 and 443 must be open in the AWS firewall.
# This script deploys locally on the VM; it does not create AWS resources.
set -euo pipefail
umask 077

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

[[ ${EUID} -eq 0 ]] || fail "Run this script with sudo on the AWS VM."
[[ $# -le 1 ]] || fail "Usage: sudo bash infra/aws/bootstrap.sh [environment-file]"
[[ -r /etc/os-release ]] || fail "Ubuntu 24.04 is required."
# This is a trusted operating-system file, not the application environment file.
. /etc/os-release
[[ ${ID:-} == ubuntu && ${VERSION_ID:-} == 24.04 ]] || fail "Ubuntu 24.04 is required."

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "$script_dir/../.." && pwd)
env_file=${1:-/srv/dealerwatch/aws.env}
[[ -f "$env_file" ]] || fail "Create the server environment file before deploying."
env_file=$(realpath -- "$env_file")
case "$env_file" in
  "$repo_dir"/*) fail "Keep the server environment file outside the repository checkout." ;;
esac
chmod 600 "$env_file"
export DW_AWS_ENV_FILE="$env_file"

install_docker_repository() {
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl --fail --silent --show-error --location \
    https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  apt-get update
}

if ! command -v docker >/dev/null 2>&1; then
  install_docker_repository
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
elif ! docker compose version >/dev/null 2>&1; then
  install_docker_repository
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-plugin docker-buildx-plugin
fi
systemctl enable --now docker
command -v python3 >/dev/null 2>&1 || fail "Python 3 is required for configuration validation."
command -v curl >/dev/null 2>&1 || fail "curl is required for the HTTPS readiness check."

compose=(docker compose --env-file "$env_file" -f "$script_dir/compose.yaml")
"${compose[@]}" config --quiet
# Parse Compose's effective environment without sourcing a file or printing secrets.
"${compose[@]}" config --format json | python3 -c '
import ipaddress
import json
import sys
from urllib.parse import urlsplit

config = json.load(sys.stdin)
env = config["services"]["dealerwatch"]["environment"]
public_ip = ipaddress.ip_address(config["services"]["caddy"]["environment"]["PUBLIC_IP"])
if public_ip.version != 4 or not public_ip.is_global:
    sys.exit("PUBLIC_IP must be the attached, globally routable static IPv4 address.")
tokens = [env.get("DW_ADMIN_TOKEN", ""), env.get("DW_REVIEWER_TOKEN", "")]
if any(len(token.strip()) < 32 for token in tokens) or tokens[0].strip() == tokens[1].strip():
    sys.exit("Set distinct administrator and reviewer tokens of at least 32 characters.")
for origin in env.get("DW_PUBLIC_ORIGINS", "").split(","):
    origin = origin.strip()
    try:
        parsed = urlsplit(origin)
        valid = (parsed.scheme == "https" and parsed.hostname and parsed.port in (None, 443)
                 and parsed.username is None and parsed.password is None and not parsed.query
                 and not parsed.fragment and parsed.path in ("", "/")
                 and not any(char in origin for char in ("*", "\\", " ", "\r", "\n", "\t", "?", "#")))
    except ValueError:
        valid = False
    if not valid:
        sys.exit("DW_PUBLIC_ORIGINS must contain exact HTTPS origins without paths or wildcards.")
if env.get("DW_DEMO") not in ("0", "1"):
    sys.exit("DW_DEMO must be 0 or 1; leave it at 0 for ordinary operation.")
print("Deployment configuration is valid.")
'

install -d -m 0750 /srv/dealerwatch
install -d -o 10001 -g 10001 -m 0750 /srv/dealerwatch/data
install -d -m 0700 /srv/dealerwatch/caddy-data /srv/dealerwatch/caddy-config
# Adapt only: this checks syntax without starting TLS or ordering a certificate.
"${compose[@]}" run --rm --no-deps caddy \
  caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null

"${compose[@]}" up --detach --build --wait --wait-timeout 180
"${compose[@]}" exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile

public_ip=$("${compose[@]}" config --format json | python3 -c \
  'import json, sys; print(json.load(sys.stdin)["services"]["caddy"]["environment"]["PUBLIC_IP"])')
curl --fail --silent --show-error --retry 30 --retry-all-errors --retry-delay 2 \
  --retry-max-time 120 --connect-timeout 5 --max-time 10 \
  "https://$public_ip/api/ready" >/dev/null
printf 'DealerWatch is ready at https://%s. Data persists in /srv/dealerwatch/data.\n' "$public_ip"
