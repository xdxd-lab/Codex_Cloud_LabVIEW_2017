#!/usr/bin/env python3
"""Local stdio MCP bridge to a PowerShell agent in the Windows guest."""
import base64
import json
import subprocess
import threading
from pathlib import Path
from mcp.server import MCPServer as FastMCP

ROOT = Path(__file__).resolve().parents[2]
TOKEN = ROOT / '.local' / 'labview-bridge-token'
RELAY = Path(__file__).with_name('relay.pl').read_text(encoding='utf-8')
LOCK = threading.Lock()
mcp = FastMCP('LabVIEW 2017 local bridge')


def request(op, **fields):
    if not TOKEN.is_file():
        raise RuntimeError('Bridge token missing; set up the Windows guest agent first.')
    token = TOKEN.read_text(encoding='ascii').strip()
    if len(token) < 32:
        raise RuntimeError('Bridge token is invalid.')
    payload = base64.b64encode(json.dumps({'token': token, 'op': op, **fields}, ensure_ascii=True).encode()).decode() + '\n'
    try:
        with LOCK:
            proc = subprocess.run(['docker', 'exec', '-i', 'labview2017-win7', 'perl', '-e', RELAY], input=payload, text=True, capture_output=True, timeout=250, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Windows bridge did not respond within 250 seconds.') from exc
    if proc.returncode:
        raise RuntimeError('Bridge transport failed: ' + proc.stderr.strip())
    try:
        response = json.loads(base64.b64decode(proc.stdout.strip(), validate=True).decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError('Windows bridge returned an invalid response.') from exc
    if not response.get('ok'):
        raise RuntimeError('Windows bridge: ' + str(response.get('error', 'unknown error')))
    return response['result']


@mcp.tool()
def labview_bridge_ping() -> dict:
    """Check that the Windows bridge agent is responding without starting LabVIEW."""
    return request('ping')


@mcp.tool()
def labview_version() -> dict:
    """Read the version of the local LabVIEW ActiveX server in the guest."""
    return request('version')


@mcp.tool()
def labview_get_control(path: str, control: str) -> dict:
    """Read a named front-panel control in a VI in the configured guest workspace."""
    return request('get_control', path=path, control=control)


if __name__ == '__main__':
    mcp.run()
