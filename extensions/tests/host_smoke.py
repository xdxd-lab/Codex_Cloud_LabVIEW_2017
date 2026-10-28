#!/usr/bin/env python3
"""Minimal repeatable validation for the Linux host companion tools."""
from __future__ import annotations

import asyncio
import csv
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "extensions/host/.venv/bin/python"
NODE = ROOT / "extensions/host/node_modules/.bin"
ARTIFACTS = ROOT / "artifacts"
RESULT: dict = {"checks": {}, "errors": []}


def check(name, fn):
    try:
        RESULT["checks"][name] = {"status": "passed", **fn()}
    except Exception as exc:  # retain concise actionable evidence
        RESULT["checks"][name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        RESULT["errors"].append(name)


def mcp_servers():
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    async def inspect(server: str):
        params = StdioServerParameters(command="sh", args=["extensions/run-mcp.sh", server], env={"PWD": str(ROOT)})
        with open(os.devnull, "w") as quiet_log:
            async with stdio_client(params, errlog=quiet_log) as (read, write):
                async with ClientSession(read, write) as session:
                    init = await asyncio.wait_for(session.initialize(), timeout=25)
                    tools = await asyncio.wait_for(session.list_tools(), timeout=25)
                    return {"tool_count": len(tools.tools), "tool_names": [t.name for t in tools.tools],
                            "server_name": init.server_info.name}

    async def run():
        results = {}
        for name in ("filesystem", "git", "fetch", "memory", "sequential-thinking"):
            try:
                results[name] = {"status": "passed", **await inspect(name)}
            except Exception as exc:
                results[name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
                RESULT["errors"].append(f"mcp.{name}")
        # Verify filesystem only exposes the wrapper's authorized workspace-data root.
        try:
            params = StdioServerParameters(command="sh", args=["extensions/run-mcp.sh", "filesystem"], env={"PWD": str(ROOT)})
            with open(os.devnull, "w") as quiet_log:
                async with stdio_client(params, errlog=quiet_log) as (read, write):
                    async with ClientSession(read, write) as session:
                        await asyncio.wait_for(session.initialize(), timeout=25)
                        tools = await session.list_tools()
                        names = {t.name for t in tools.tools}
                        list_tool = "list_directory" if "list_directory" in names else "list_directory_with_sizes"
                        listed = await asyncio.wait_for(session.call_tool(list_tool, {"path": str(ROOT / "workspace-data")}, read_timeout_seconds=25), timeout=25)
                        text = "\n".join(getattr(c, "text", "") for c in listed.content)
                        allowed = await asyncio.wait_for(session.call_tool("list_allowed_directories", {}), timeout=25)
                        allowed_text = "\n".join(getattr(c, "text", "") for c in allowed.content)
                        allowed_paths = [line.strip() for line in allowed_text.splitlines() if line.startswith("/")]
                        ok = not listed.is_error and allowed_paths == [str(ROOT / "workspace-data")]
                        results["filesystem_listing"] = {"status": "passed" if ok else "failed",
                                                          "root": str(ROOT / "workspace-data"),
                                                          "response_excerpt": text[:400], "allowed_directories": allowed_text[:300]}
                        if not ok:
                            RESULT["errors"].append("mcp.filesystem_listing")
        except Exception as exc:
            cause = exc
            while getattr(cause, "exceptions", None):
                cause = cause.exceptions[0]
            results["filesystem_listing"] = {"status": "failed", "error": f"{type(cause).__name__}: {cause}"}
            RESULT["errors"].append("mcp.filesystem_listing")
        return results

    RESULT["checks"]["mcp"] = asyncio.run(run())


def py_formats():
    import nbformat
    from nbclient import NotebookClient
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader
    import pdfplumber

    ARTIFACTS.mkdir(exist_ok=True)
    work = ARTIFACTS / "host-smoke-data"
    work.mkdir(exist_ok=True)
    # A minimal executable notebook cell.
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("answer = 6 * 7\nassert answer == 42\nanswer")])
    NotebookClient(nb, timeout=30, kernel_name="python3").execute(cwd=str(work))
    nbformat.write(nb, work / "smoke.ipynb")
    notebook = {"executed": True, "cell_output": nb.cells[0].outputs[-1].data.get("text/plain")}

    # CSV and Excel write/read round trips.
    df = pd.DataFrame({"name": ["alpha", "beta"], "value": [3, 9]})
    csv_path = work / "roundtrip.csv"
    xlsx_path = work / "roundtrip.xlsx"
    df.to_csv(csv_path, index=False)
    with csv_path.open(newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    df.to_excel(xlsx_path, index=False)
    read_xlsx = pd.read_excel(xlsx_path)
    assert csv_rows[1]["value"] == "9" and read_xlsx.equals(df)

    # Generate and extract text from a local PDF.
    pdf_path = work / "smoke.pdf"
    c = canvas.Canvas(str(pdf_path)); c.drawString(72, 720, "Host validation PDF 42"); c.save()
    extracted = PdfReader(str(pdf_path)).pages[0].extract_text()
    with pdfplumber.open(pdf_path) as pdf:
        plumber_pages = len(pdf.pages)
    assert "Host validation PDF 42" in extracted and plumber_pages == 1

    # Save a real Matplotlib render.
    fig, ax = plt.subplots(); ax.plot([0, 1], [0, 1]); ax.set_title("host smoke"); fig.savefig(work / "plot.png"); plt.close(fig)
    versions = {}
    for package in ("mcp", "openai", "jupyterlab", "ipykernel", "pandas", "matplotlib", "openpyxl", "pypdf", "pdfplumber", "reportlab"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "missing"
    return {"python": sys.version.split()[0], "versions": versions,
            "notebook": notebook, "csv_excel_roundtrip": "passed",
            "pdf": {"page_count_pdfplumber": plumber_pages, "text_extracted": True},
            "matplotlib_png_bytes": (work / "plot.png").stat().st_size}


def browser():
    script = r'''const { chromium } = require(process.env.PW_MODULE);
(async () => { const browser = await chromium.launch({headless:true, executablePath:"/usr/bin/chromium", args:["--no-sandbox"]});
const page = await browser.newPage({viewport:{width:640,height:360}});
await page.setContent("<!doctype html><title>Host smoke</title><main style='font:32px sans-serif;color:#146'>Chromium works</main>");
const title = await page.title(); await page.screenshot({path:process.env.PW_SHOT}); await browser.close();
if (title !== "Host smoke") process.exit(2); })().catch(e=>{console.error(e.message);process.exit(1)});'''
    shot = ARTIFACTS / "host-smoke-browser.png"
    env = os.environ.copy()
    env.update(PW_MODULE=str(ROOT / "extensions/host/node_modules/playwright"), PW_SHOT=str(shot))
    proc = subprocess.run(["node", "-e", script], cwd=ROOT, env=env, text=True, capture_output=True, timeout=60)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[-500:])
    if not shot.is_file() or shot.stat().st_size < 1000:
        raise RuntimeError("screenshot missing or unexpectedly small")
    return {"executable": "/usr/bin/chromium", "headless": True, "screenshot": str(shot.relative_to(ROOT)), "bytes": shot.stat().st_size}


def skill_manifest():
    manifest = json.loads((ROOT / "extensions/skills.lock.json").read_text())
    results, missing, mismatches = {}, [], []
    for rel, expected in manifest["sha256"].items():
        path = ROOT / ".agents/skills" / rel
        if not path.is_file():
            missing.append(rel)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        results[rel] = actual == expected
        if actual != expected:
            mismatches.append(rel)
    licenses = {name: (ROOT / ".agents/skills" / name / "LICENSE.txt").is_file() for name in manifest["skills"]}
    if missing or mismatches or not all(licenses.values()):
        raise RuntimeError(f"missing={missing[:3]}, hash_mismatches={mismatches[:3]}, licenses_missing={[k for k,v in licenses.items() if not v]}")
    return {"manifest_entries": len(results), "all_hashes_match": True, "licenses_present": licenses}


def main():
    RESULT["generated_at_utc"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    check("python_workflows", py_formats)
    try:
        mcp_servers()
    except Exception as exc:
        RESULT["checks"]["mcp"] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        RESULT["errors"].append("mcp")
    check("browser", browser)
    check("skills", skill_manifest)
    ARTIFACTS.mkdir(exist_ok=True)
    out = ARTIFACTS / "host-validation.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"result": str(out.relative_to(ROOT)), "errors": RESULT["errors"],
                      "check_names": list(RESULT["checks"])}, ensure_ascii=False))
    return bool(RESULT["errors"])


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
