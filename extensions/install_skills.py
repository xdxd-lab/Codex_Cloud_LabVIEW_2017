#!/usr/bin/env python3
"""Install the vendored skill snapshot without overwriting customized skills."""
import argparse
import hashlib
import os
import shutil
from pathlib import Path


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / ".agents" / "skills"
    target = args.destination or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    target.mkdir(parents=True, exist_ok=True)
    for directory in sorted(source.iterdir()):
        if not directory.is_dir():
            continue
        destination = target / directory.name
        if destination.exists():
            if fingerprint(directory) != fingerprint(destination):
                raise FileExistsError(f"Refusing to replace a different skill: {destination}")
            print(f"Already installed: {directory.name}")
        else:
            shutil.copytree(directory, destination)
            print(f"Installed: {directory.name}")


if __name__ == "__main__":
    main()
