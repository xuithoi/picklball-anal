#!/usr/bin/env bash
# Install a verified Compose plugin. An optional destination supports local validation.
set -euo pipefail
if [ "$(uname -m)" != x86_64 ]; then
  echo 'This Compose installer supports Linux x86_64 only.' >&2
  exit 1
fi
compose_version=v2.39.4
compose_sha256=7af95166a730b87e172d4fc9aefea8725d3c6c7327d59149267b452114ddb7d4
compose_image=docker/compose-bin:v2.39.4@sha256:2f2ab50fbed6b13eab5c832d9be82eed4959aae4c4da9018fc7b45e8b3f96d99
compose_destination="${1:-/usr/local/lib/docker/cli-plugins/docker-compose}"
if [ -x "$compose_destination" ] && [ "$("$compose_destination" version --short)" = "${compose_version#v}" ]; then
  "$compose_destination" version
  exit 0
fi
compose_tmp="$(mktemp -d)"
compose_container=''
cleanup() {
  if [ -n "$compose_container" ]; then
    docker rm "$compose_container" >/dev/null 2>&1 || true
  fi
  rm -rf "$compose_tmp"
}
trap cleanup EXIT
verify_compose() {
  printf '%s  %s\n' "$compose_sha256" "$compose_tmp/docker-compose" | sha256sum --check
}
download_from_registry() {
  docker pull --platform linux/amd64 "$compose_image" || return
  compose_container="$(docker create --platform linux/amd64 --entrypoint /docker-compose "$compose_image" version)" || return
  docker cp "$compose_container:/docker-compose" "$compose_tmp/docker-compose" || return
  verify_compose
}
compose_url="https://github.com/docker/compose/releases/download/$compose_version/docker-compose-linux-x86_64?download=1"
if download_from_registry; then
  echo 'Verified Compose binary from the pinned official Docker image.'
elif curl --fail --location --retry 2 --connect-timeout 10 --max-time 60 "$compose_url" -o "$compose_tmp/docker-compose" && verify_compose; then
  echo 'Verified Compose release download.'
else
  echo 'Both verified Compose download methods failed; no plugin was installed.' >&2
  exit 1
fi

install -d "$(dirname "$compose_destination")"
install -m 0755 "$compose_tmp/docker-compose" "$compose_destination"
"$compose_destination" version
