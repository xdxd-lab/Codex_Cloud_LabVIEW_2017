#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tools="$base/extensions/host"
mkdir -p "$base/workspace-data" "$base/.local"
case "${1:-}" in
  filesystem) exec "$tools/node_modules/.bin/mcp-server-filesystem" "$base/workspace-data" ;;
  git) exec "$tools/.venv/bin/mcp-server-git" --repository "$base" ;;
  fetch)
    export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
    if [ -n "${HTTPS_PROXY:-}" ]; then
      exec "$tools/.venv/bin/mcp-server-fetch" --proxy-url "$HTTPS_PROXY"
    fi
    exec "$tools/.venv/bin/mcp-server-fetch"
    ;;
  memory)
    export MEMORY_FILE_PATH="$base/.local/memory.jsonl"
    exec "$tools/node_modules/.bin/mcp-server-memory"
    ;;
  sequential-thinking)
    export DISABLE_THOUGHT_LOGGING=true
    exec "$tools/node_modules/.bin/mcp-server-sequential-thinking"
    ;;
  *) echo "Usage: $0 {filesystem|git|fetch|memory|sequential-thinking}" >&2; exit 2 ;;
esac
