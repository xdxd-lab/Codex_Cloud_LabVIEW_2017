#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir -p "$root/.local" "$root/data/bridge-media"
umask 077
BRIDGE_ROOT="$root" python3 - <<'PY'
import os, secrets, shutil
from pathlib import Path
root = Path(os.environ['BRIDGE_ROOT'])
token = root / '.local' / 'labview-bridge-token'
if not token.exists():
    token.write_text(secrets.token_hex(32) + '\n', encoding='ascii')
token.chmod(0o600)
shutil.copyfile(token, root / 'data/bridge-media/token.txt')
shutil.copyfile(root / 'extensions/labview-bridge/guest-agent.ps1', root / 'data/bridge-media/guest-agent.ps1')
PY
# The running container must have this repository's data directory mounted at /vm.
docker exec labview2017-win7 genisoimage -quiet -J -R -V LVBRIDGE -o /vm/labview-bridge.iso /vm/bridge-media
printf '%s\n' 'Bridge media prepared at data/labview-bridge.iso. Attach it to the guest CD drive.'
