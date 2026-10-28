#!/usr/bin/env python3
"""Capture the local QEMU VNC display and optionally send basic input."""

import argparse
import json
import socket
import struct
import time

from PIL import Image


def read_exact(sock, count):
    data = bytearray()
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise ConnectionError("VNC connection closed")
        data.extend(part)
    return bytes(data)


def connect(host, port):
    sock = socket.create_connection((host, port), timeout=30)
    version = read_exact(sock, 12)
    if not version.startswith(b"RFB 003."):
        raise ValueError(f"Unsupported VNC version: {version!r}")
    sock.sendall(b"RFB 003.008\n")
    count = read_exact(sock, 1)[0]
    if count == 0:
        length = struct.unpack(">I", read_exact(sock, 4))[0]
        raise ConnectionError(read_exact(sock, length).decode("utf-8", "replace"))
    methods = read_exact(sock, count)
    if 1 not in methods:
        raise ConnectionError("VNC server does not allow unauthenticated local access")
    sock.sendall(b"\x01")
    result = struct.unpack(">I", read_exact(sock, 4))[0]
    if result:
        raise ConnectionError(f"VNC security result {result}")
    sock.sendall(b"\x01")
    init = read_exact(sock, 24)
    width, height = struct.unpack(">HH", init[:4])
    name_length = struct.unpack(">I", init[20:24])[0]
    read_exact(sock, name_length)
    pixel_format = struct.pack(">BBBBHHHBBBxxx", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
    sock.sendall(b"\x00\x00\x00\x00" + pixel_format)
    sock.sendall(struct.pack(">BBHi", 2, 0, 1, 0))
    return sock, width, height


KEYS = {
    "enter": 0xFF0D,
    "tab": 0xFF09,
    "space": 0x20,
    "escape": 0xFF1B,
    "backspace": 0xFF08,
    "up": 0xFF52,
    "down": 0xFF54,
    "left": 0xFF51,
    "right": 0xFF53,
    "home": 0xFF50,
    "end": 0xFF57,
    "pageup": 0xFF55,
    "pagedown": 0xFF56,
    "f8": 0xFFC5,
    "super": 0xFFEB,
    "ctrl": 0xFFE3,
    "alt": 0xFFE9,
    "delete": 0xFFFF,
}


def send_key(sock, key):
    code = KEYS.get(key.lower(), ord(key) if len(key) == 1 else None)
    if code is None:
        raise ValueError(f"Unknown key: {key}")
    for down in (1, 0):
        sock.sendall(struct.pack(">BBHI", 4, down, 0, code))
        time.sleep(0.04)


def send_click(sock, x, y):
    sock.sendall(struct.pack(">BBHH", 5, 1, x, y))
    time.sleep(0.1)
    sock.sendall(struct.pack(">BBHH", 5, 0, x, y))


def send_chord(sock, chord):
    names = chord.lower().split("+")
    codes = [KEYS.get(name, ord(name) if len(name) == 1 else None) for name in names]
    if None in codes:
        raise ValueError(f"Unknown chord: {chord}")
    for code in codes:
        sock.sendall(struct.pack(">BBHI", 4, 1, 0, code))
        time.sleep(0.04)
    for code in reversed(codes):
        sock.sendall(struct.pack(">BBHI", 4, 0, 0, code))
        time.sleep(0.04)


def capture(sock, width, height):
    sock.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, width, height))
    canvas = Image.new("RGB", (width, height))
    while True:
        kind = read_exact(sock, 1)[0]
        if kind == 2:
            continue  # bell
        if kind == 3:
            length = struct.unpack(">I", read_exact(sock, 7)[3:7])[0]
            read_exact(sock, length)
            continue
        if kind != 0:
            raise ValueError(f"Unexpected VNC message {kind}")
        count = struct.unpack(">H", read_exact(sock, 3)[1:3])[0]
        for _ in range(count):
            x, y, w, h, encoding = struct.unpack(">HHHHi", read_exact(sock, 12))
            if encoding == -223:
                width, height = w, h
                canvas = Image.new("RGB", (width, height))
            elif encoding == 0:
                raw = read_exact(sock, w * h * 4)
                tile = Image.frombytes("RGB", (w, h), raw, "raw", "BGRX")
                canvas.paste(tile, (x, y))
            else:
                raise ValueError(f"Unexpected VNC encoding {encoding}")
        return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5900)
    parser.add_argument("--key", action="append", default=[])
    parser.add_argument("--text", action="append", default=[])
    parser.add_argument("--chord", action="append", default=[])
    parser.add_argument("--click", nargs=2, type=int, action="append", default=[])
    parser.add_argument("--wait", type=float, default=0)
    args = parser.parse_args()
    sock, width, height = connect(args.host, args.port)
    with sock:
        for key in args.key:
            send_key(sock, key)
        for value in args.text:
            for character in value:
                send_key(sock, character)
        for chord in args.chord:
            send_chord(sock, chord)
        for x, y in args.click:
            send_click(sock, x, y)
        if args.wait:
            time.sleep(args.wait)
        image = capture(sock, width, height)
        image.save(args.output)
        print(json.dumps({"output": args.output, "size": image.size}))


if __name__ == "__main__":
    main()
