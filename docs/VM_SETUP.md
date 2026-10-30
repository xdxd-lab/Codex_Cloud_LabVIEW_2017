# Codex Cloud LabVIEW 2017

Reproducible QEMU setup for Windows 7 x64 and LabVIEW 2017 32-bit in a Codex cloud workspace. It uses software CPU emulation because the current cloud executor has no `/dev/kvm`.

## Start the VM

```sh
mkdir -p data
docker build -t labview2017-qemu .
docker run --rm --name labview2017-win7 \
  -p 127.0.0.1:5900:5900 \
  -v "$PWD/data:/vm" \
  labview2017-qemu
```

The first start creates `data/win7-labview2017.qcow2` as a sparse 24 GB disk. Put a licensed Windows 7 x64 installation image at `data/windows7-x64.iso` before first boot. Connect a VNC client to `127.0.0.1:5900` to install Windows. Then install the licensed LabVIEW 2017 32-bit distribution inside Windows. The VNC port is bound to localhost on the Docker host.

For the smaller NI LabVIEW 2017 SP1 English 32-bit installer, place NI's `2017sp1LV-WinEng_VIPMfix.zip` in `data/` and create a virtual installation CD:

```sh
docker run --rm -v "$PWD/data:/vm" \
  --entrypoint /usr/local/bin/prepare-installer labview2017-qemu
```

The VM automatically attaches `data/labview2017sp1.iso` when present. This NI package is about 1.5 GB compressed and is separate from NI's large combined driver media. No driver bundle is installed by this procedure.

The `.gitignore` intentionally excludes operating system media, VM disks, and installers. The GitHub repository currently contains configuration only; it cannot restore a previous VM disk or VI unless those artifacts are recovered separately.
