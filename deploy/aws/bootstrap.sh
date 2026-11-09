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
    if ! docker compose version >/dev/null 2>&1; then
      compose_version=v2.39.4
      compose_asset=docker-compose-linux-x86_64
      compose_tmp="$(mktemp -d)"
      trap 'rm -rf "$compose_tmp"' EXIT
      compose_url="https://github.com/docker/compose/releases/download/$compose_version/$compose_asset"
      curl --fail --location --retry 2 "$compose_url?download=1" -o "$compose_tmp/$compose_asset"
      curl --fail --location --retry 2 "$compose_url.sha256" -o "$compose_tmp/$compose_asset.sha256"
      (cd "$compose_tmp" && sha256sum --check "$compose_asset.sha256")
      install -d /usr/local/lib/docker/cli-plugins
      install -m 0755 "$compose_tmp/$compose_asset" /usr/local/lib/docker/cli-plugins/docker-compose
    fi
    ;;
  *) echo 'Supported systems: Amazon Linux 2023 or Ubuntu 24.04 LTS.' >&2; exit 1 ;;
esac
systemctl enable --now docker
docker compose version
