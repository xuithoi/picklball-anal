#!/usr/bin/env bash
# Backwards-compatible entrypoint. The installer now also supports Amazon Linux.
set -euo pipefail
exec bash "$(dirname "$0")/bootstrap.sh" "$@"
