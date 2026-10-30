# Experimental LabVIEW 2017 bridge

The host MCP server communicates with a Windows 7 PowerShell agent via a localhost-only listener inside the QEMU container. The agent uses LabVIEW ActiveX, so LabVIEW must already be running. The guest reconnects to `10.0.2.2:18765`; the shared token is stored outside version control. The project MCP configuration is loaded when Codex starts in this repository; start a new session to discover it.

Verified end to end: MCP initialization, tool listing, bridge ping, and reading LabVIEW 17.0.1 via ActiveX. Reading a VI control is implemented but not yet verified on a real VI. The agent limits VI paths to `%USERPROFILE%\Documents\LabVIEW Data\Codex` and currently provides no editing or running tool. The guest agent is not automatically started on Windows login. The VM and `.local` token need to persist for the bridge to work.

The VM uses an evaluation license; activation is handled separately using the user's NI license. The TCP listener is bound to localhost inside the VM container; do not publish its port. The transport is not encrypted and is intended for this local VM only.

## Prepare the guest agent

Start the QEMU container with this repository's `data` directory mounted at `/vm`, as described in `docs/VM_SETUP.md`. From the repository root run `sh extensions/labview-bridge/prepare-media.sh`. It generates a new token only if `.local/labview-bridge-token` does not exist and creates a CD image containing the guest script and a copy of that token. Both `.local` and `data` must stay private and are ignored by Git.

Attach `data/labview-bridge.iso` to the guest's existing second CD device through the QEMU monitor. In Windows, copy `guest-agent.ps1` and `token.txt` from that CD to `%LOCALAPPDATA%\LabVIEWBridge`. In PowerShell, launch the copied script:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\LabVIEWBridge\guest-agent.ps1"
```

Keep LabVIEW open and the agent running. The agent currently must be restarted after logging back into Windows. The ISO, guest token and host token must match; if you regenerate a token, update the guest copy. For an existing VM, preserve the original token securely if you intend to reconnect without updating the guest.
