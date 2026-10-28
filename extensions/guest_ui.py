#!/usr/bin/env python3
"""Send an ordered action list to the local VM's VNC display."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vnc_control import capture, connect, send_chord, send_click, send_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--actions", default="[]")
    args = parser.parse_args()
    sock, width, height = connect("127.0.0.1", 5900)
    with sock:
        for action in json.loads(args.actions):
            kind, *values = action
            if kind == "click":
                send_click(sock, *values)
            elif kind == "key":
                send_key(sock, values[0])
            elif kind == "chord":
                send_chord(sock, values[0])
            elif kind == "text":
                for character in values[0]:
                    send_key(sock, character)
            elif kind == "wait":
                if not 0 <= values[0] <= 30:
                    raise ValueError("Each wait must be between 0 and 30 seconds")
                time.sleep(values[0])
            else:
                raise ValueError(f"Unknown action: {kind}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result = capture(sock, width, height)
        result.save(args.output)
        print(json.dumps({"image": str(args.output), "size": result.size}))


if __name__ == "__main__":
    main()
