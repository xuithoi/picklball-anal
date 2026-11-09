#!/usr/bin/env bash
# Run with sudo on EC2. Supports the user's Amazon Linux 2023 and Ubuntu 24.04.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'Run with sudo on the EC2 host.' >&2
  exit 1
fi
if [ "$(uname -m)" != x86_64 ]; then
  echo 'The pinned CPU PyTorch image requires x86_64.' >&2
  exit 1
fi
. /etc/os-release
case "${ID:-}:${VERSION_ID:-}" in
  ubuntu:24.04)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y docker.io docker-compose-v2 ca-certificates curl openssl python3
    ;;
  amzn:2023)
    dnf install -y docker git ca-certificates openssl python3
    command -v curl >/dev/null || dnf install -y curl-minimal
    ;;
  *) echo 'Supported systems: Amazon Linux 2023 or Ubuntu 24.04 LTS.' >&2; exit 1 ;;
esac
systemctl enable --now docker
if ! docker compose version >/dev/null 2>&1; then
  bash "$(dirname "$0")/install-compose.sh"
fi
docker compose version
