#!/bin/sh
set -eu

disk=/vm/win7-labview2017.qcow2
iso=/vm/windows7-x64.iso
labview_iso=/vm/labview2017sp1.iso

if [ ! -f "$disk" ]; then
    qemu-img create -f qcow2 "$disk" 24G
fi

set -- qemu-system-x86_64 \
    -machine pc \
    -accel tcg \
    -cpu qemu64 \
    -smp 2 \
    -m 4096 \
    -drive "file=$disk,format=qcow2,if=ide" \
    -vga std \
    -usb -device usb-tablet \
    -netdev user,id=net0 \
    -device e1000,netdev=net0 \
    -display none \
    -vnc 0.0.0.0:0 \
    -monitor "unix:/vm/qemu-monitor.sock,server,nowait"

if [ -f "$iso" ]; then
    set -- "$@" -drive "file=$iso,media=cdrom,readonly=on,if=ide" -boot order=d
else
    set -- "$@" -boot order=c
fi

if [ -f "$labview_iso" ]; then
    set -- "$@" -drive "file=$labview_iso,media=cdrom,readonly=on,if=ide"
fi

exec "$@"
