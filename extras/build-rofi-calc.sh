#!/usr/bin/env bash
# Build rofi-calc (live calculator tab for the launcher) into ~/.local/lib/rofi/calc.so.
# Only needed where your distro doesn't package it (Arch: `pacman -S rofi-calc`).
#
# Build deps — Debian/Ubuntu: sudo apt install meson ninja-build rofi-dev libqalculate-dev qalc
#              Fedora:        sudo dnf install meson ninja-build rofi-devel libqalculate-devel qalculate
#
# rofi-calc's plugin API follows rofi's, so newer tags don't build against older rofi
# (Debian 13 ships rofi 1.7.5 → v2.3.3). Tags are tried newest-first until one builds.
set -euo pipefail

SRC="${XDG_DATA_HOME:-$HOME/.local/share}/harbor/src/rofi-calc"
DEST="$HOME/.local/lib/rofi"
TAGS=(v2.5.1 v2.4.1 v2.3.3)

for cmd in git meson ninja pkg-config qalc; do
    command -v "$cmd" >/dev/null || { echo "missing: $cmd (see the header of this script)" >&2; exit 1; }
done
pkg-config --exists rofi || { echo "missing: rofi development headers (rofi-dev / rofi-devel)" >&2; exit 1; }

mkdir -p "$(dirname "$SRC")" "$DEST"
for tag in "${TAGS[@]}"; do
    echo "→ trying rofi-calc $tag against rofi $(pkg-config --modversion rofi)"
    rm -rf "$SRC"
    git -c advice.detachedHead=false clone -q --depth 1 --branch "$tag" \
        https://github.com/svenstaro/rofi-calc.git "$SRC"
    if (cd "$SRC" && meson setup build --prefix="$HOME/.local" >/dev/null && ninja -C build >/dev/null 2>&1); then
        install -m 755 "$SRC/build/src/libcalc.so" "$DEST/calc.so"
        echo "✓ installed $DEST/calc.so (rofi-calc $tag) — the launcher's Calc tab is on"
        exit 0
    fi
    echo "  $tag doesn't build here, trying an older one"
done
echo "✗ no rofi-calc tag built against this rofi" >&2
exit 1
