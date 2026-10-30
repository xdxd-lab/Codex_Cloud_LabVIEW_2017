#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
uv sync --locked --project "$base/extensions/host"
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --prefix "$base/extensions/host"
python3 "$base/extensions/install_skills.py"
mkdir -p "$base/workspace-data" "$base/.local"
echo "Host dependencies and skills installed. Restart Codex to discover new skills and project MCP settings."
