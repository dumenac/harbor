#!/usr/bin/env bash
# Build i3lock-color (the lock screen's live clock and accent ring) into ~/.local/opt/i3lock-color.
# Only needed where your distro doesn't package it (Arch: `pacman -S i3lock-color`).
# Without it Harbor falls back to plain i3lock with the same blurred, captioned background.
#
# Build deps — Debian/Ubuntu:
#   sudo apt install autoconf automake gcc make pkg-config libpam0g-dev libcairo2-dev \
#     libfontconfig-dev libxcb-composite0-dev libev-dev libx11-xcb-dev libxcb-xkb-dev \
#     libxcb-xinerama0-dev libxcb-randr0-dev libxcb-image0-dev libxcb-util0-dev \
#     libxcb-xrm-dev libxkbcommon-dev libxkbcommon-x11-dev libjpeg-dev libgif-dev
#
# It authenticates through PAM service "i3lock": keep your distro's i3lock package installed
# so /etc/pam.d/i3lock exists.
set -euo pipefail

TAG=2.13.c.5
SRC="${XDG_DATA_HOME:-$HOME/.local/share}/harbor/src/i3lock-color"
PREFIX="$HOME/.local/opt/i3lock-color"

for cmd in git autoreconf make gcc pkg-config; do
    command -v "$cmd" >/dev/null || { echo "missing: $cmd (see the header of this script)" >&2; exit 1; }
done
[ -e /etc/pam.d/i3lock ] || echo "! /etc/pam.d/i3lock not found — install your distro's i3lock package first" >&2

rm -rf "$SRC"
mkdir -p "$(dirname "$SRC")"
git -c advice.detachedHead=false clone -q --depth 1 --branch "$TAG" \
    https://github.com/Raymo111/i3lock-color.git "$SRC"
cd "$SRC"
autoreconf -fi >/dev/null 2>&1
mkdir -p build && cd build
../configure --prefix="$PREFIX" --sysconfdir="$PREFIX/etc" --disable-sanitizers >/dev/null
make -j"$(nproc)" >/dev/null
install -Dm 755 i3lock "$PREFIX/bin/i3lock-color"
echo "✓ installed $PREFIX/bin/i3lock-color ($TAG) — harbor picks it up automatically"
