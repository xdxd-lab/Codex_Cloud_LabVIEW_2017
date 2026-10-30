# Codex Cloud LabVIEW 2017 MCP

This repository contains the QEMU, Windows guest bridge, and Codex MCP configuration used for a LabVIEW 2017 SP1 32-bit experiment. It is a recipe for rebuilding the environment: it does **not** contain a snapshot of the Windows VM, installed LabVIEW, VIs, installers, activation, or credentials. Rebuilding requires licensed installation media and sufficient disk space. The last live test successfully read LabVIEW version 17.0.1 through MCP; reading an actual VI control is not yet verified.

## Build the host and Windows VM

1. In a Codex Cloud environment associated with this repository, install `uv`, Python 3.12, Node.js 24, npm and Docker. From the repository root run `sh extensions/setup-host.sh` to install the pinned host dependencies and skills.
2. Follow the VM instructions in [VM setup](docs/VM_SETUP.md). The VM uses QEMU software emulation, 2 vCPU, 4 GiB RAM and a 24 GiB virtual disk. Install licensed Windows 7 x64 and LabVIEW 2017 SP1 32-bit, VIPM and the selected packages. Startup and installation can be slow. Windows 7 and LabVIEW evaluation require appropriate licensing and separate maintenance.
3. Start Windows and LabVIEW, then follow [bridge setup](extensions/labview-bridge/README.md). Start a new Codex session in this repository for `.codex/config.toml` and skills to load. The bridge provides ping, version, and a restricted control-read tool; it does not currently create, edit or run VIs.

A Codex Cloud Environment and this GitHub repository are distinct: create an Environment in the Codex interface and choose this repository. The Environment does not preserve a running VM or its disk automatically; keep the disk and bridge token in durable private storage if you need to restore the same machine. Never commit them or software installers.
