#!/usr/bin/env python3
"""Resolve public VIPM feeds for LabVIEW 2017 and download pinned packages."""
import argparse
import configparser
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

FEEDS = [
    "https://s3-us-west-1.amazonaws.com/jki-vi-package-network/packages/index.vipr",
    "https://download.ni.com/evaluation/labview/lvtn/vipm/index.vipr",
]
ROOTS = {
    "jdp_science_jsontext": "1.9.1.125",
    "lava_lib_json_api": "1.5.5.41",
    "jki_lib_rest_client": "1.3.3.25",
}


def version(value):
    numbers = tuple(int(x) for x in re.findall(r"\d+", value))
    return numbers + (0,) * max(0, 8 - len(numbers))


def satisfies(actual, expression):
    if not expression.strip():
        return True
    match = re.fullmatch(r"\s*(>=|<=|==|=|>|<)?\s*([\d.]+)\s*", expression)
    if not match:
        raise ValueError(f"Unsupported version constraint: {expression}")
    op, requested = match.groups()
    a, b = version(actual), version(requested)
    return {">=": a >= b, "<=": a <= b, "=": a == b, "==": a == b,
            ">": a > b, "<": a < b, None: a == b}[op]


def compatible(expression):
    if not expression:
        return False
    parts = expression.replace("LabVIEW", "").split(",")
    return any(satisfies("17.0", x.replace("x86", "")) for x in parts if "x64" not in x)


def dependency(value):
    match = re.fullmatch(r"(.+?)(>=|<=|==|=|>|<)([\d.]+)", value.strip())
    if match:
        return match.group(1), match.group(2) + match.group(3)
    return value.strip(), ""


def fetch_catalog():
    catalog = {}
    for feed in FEEDS:
        with urllib.request.urlopen(feed, timeout=40) as response:
            raw = response.read()
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read_string(raw.decode("cp1252", errors="replace"))
        for section in parser.sections():
            match = re.fullmatch(r"Package (.+?)-(\d.*)", section)
            if not match:
                continue
            name, number = match.groups()
            info = parser[section]
            lv = info.get("platform.exclusive_labview_version", "")
            if not compatible(lv) or re.search(r"alpha|beta", number, re.I):
                continue
            vipm = info.get("platform.exclusive_vipm_version", "0")
            if version(vipm) > version("2017"):
                continue
            path = info.get("package.url", "")
            if not path:
                continue
            url = urllib.parse.urljoin(feed, path)
            parsed = urllib.parse.urlsplit(url)
            url = urllib.parse.urlunsplit(parsed._replace(path=urllib.parse.quote(parsed.path, safe="/%")))
            catalog.setdefault(name, {})[number] = {
                "name": name, "version": number, "url": url,
                "md5": info.get("package.md5", ""), "labview_constraint": lv,
                "dependencies": [dependency(x) for x in info.get("dependencies.requires", "").split(",") if x.strip()],
            }
    return catalog


def resolve(catalog):
    constraints = {name: ["=" + num] for name, num in ROOTS.items()}
    selected = {}
    for _ in range(100):
        changed = False
        for name, rules in list(constraints.items()):
            choices = [x for x in catalog.get(name, {}).values()
                       if all(satisfies(x["version"], rule) for rule in rules)]
            if not choices:
                raise RuntimeError(f"No LabVIEW 2017 / VIPM 2017 compatible version: {name} {rules}")
            choice = max(choices, key=lambda x: version(x["version"]))
            if selected.get(name) != choice:
                selected[name] = choice
                changed = True
            for dep, rule in choice["dependencies"]:
                if dep not in constraints or rule not in constraints[dep]:
                    constraints.setdefault(dep, []).append(rule)
                    changed = True
        if not changed:
            return sorted(selected.values(), key=lambda x: x["name"])
    raise RuntimeError("Dependency resolution did not converge")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--locked", action="store_true", help="Use only the existing manifest and verify SHA-256")
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    packages = (json.loads(args.manifest.read_text())["packages"] if args.locked
                else resolve(fetch_catalog()))
    for item in packages:
        filename = urllib.parse.unquote(urllib.parse.urlsplit(item["url"]).path.rsplit("/", 1)[-1])
        target = args.destination / filename
        if not target.exists():
            with urllib.request.urlopen(item["url"], timeout=60) as response:
                raw = response.read()
            target.write_bytes(raw)
        else:
            raw = target.read_bytes()
        digest = hashlib.md5(raw).hexdigest()
        if item["md5"] and digest != item["md5"].lower():
            raise RuntimeError(f"Feed checksum mismatch: {filename}")
        sha256 = hashlib.sha256(raw).hexdigest()
        if args.locked and sha256 != item.get("sha256"):
            raise RuntimeError(f"Locked SHA-256 mismatch: {filename}")
        item.update(filename=filename, bytes=len(raw), sha256=sha256)
        print(f"Downloaded {filename} ({len(raw)} bytes)", flush=True)
    if not args.locked:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps({"target_labview": "2017 32-bit", "roots": ROOTS, "packages": packages}, indent=2) + "\n")


if __name__ == "__main__":
    main()
