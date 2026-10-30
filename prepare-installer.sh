#!/bin/sh
set -eu

archive=/vm/2017sp1LV-WinEng_VIPMfix.zip
image=/vm/labview2017sp1.iso

if [ ! -f "$archive" ]; then
    echo "Missing NI installer archive: $archive" >&2
    exit 1
fi

work=$(mktemp -d /vm/.labview-media-XXXXXX)
trap 'rm -rf "$work"' EXIT INT TERM
unzip -q "$archive" -d "$work"
genisoimage -quiet -R -J -joliet-long -V LABVIEW2017SP1 -o "$image" "$work"
echo "Created $image"
