# LabVIEW 2017 companion tools

The guest target is LabVIEW 2017 SP1, 32-bit, on Windows 7 x64 with VIPM 2017. The pinned packages are JSONtext, LAVA JSON API and JKI HTTP REST Client, together with their required JDP and OpenG dependencies. `packages.lock.json` records versions, source URLs and SHA-256 hashes; package installers and virtual disks are not stored in this repository.

To download and verify the pinned packages:

```sh
python3 extensions/resolve_packages.py --locked --manifest extensions/packages.lock.json /path/to/packages
```

Make these files available to the Windows guest and use VIPM's File > Open Package File(s) to select the eight `.vip` files, then choose Add To Library & Install. VIPM may restart LabVIEW and require interaction with the LabVIEW licensing dialog. Verify the results in VIPM. LabVIEW needs an appropriate NI license; no activation credentials are included here. Some JSONtext VIM features may require a LabVIEW 2017 SP1 f-series patch; check NI's guidance for the particular features in use.

LV-JSON is omitted from the default package set because its published VIPM dependency chain includes the complete OpenG toolkit and a legacy hardware driver. VIPM API requires a suitable VIPM license. The currently published CalmyJane LabVIEW Assistant project targets a newer LabVIEW and Python runtime than this Windows 7 / LabVIEW 2017 configuration.

## Host companion setup

From the repository root on a compatible Linux host with `uv`, Python 3.12, Node.js 24 and npm available:

```sh
sh extensions/setup-host.sh
python3 extensions/tests/host_smoke.py
```

The setup installs pinned Python and npm dependencies and copies six pinned OpenAI skills without replacing existing user skills. Start a new Codex session in this repository to load its project configuration. The filesystem MCP server is limited to `workspace-data`, while Git MCP is scoped to this repository. Memory data is stored in `.local`; both directories are ignored by Git. Fetch inherits the host network configuration. The Playwright smoke test expects a Chromium executable at `/usr/bin/chromium`. OpenAI SDK installation does not provide an API key or activate a paid service. The six skills are from a pinned snapshot of the deprecated OpenAI skills repository; see `skills.lock.json` and individual licenses.
