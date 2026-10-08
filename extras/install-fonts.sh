#!/usr/bin/env bash
# Install the three fonts Harbor uses into ~/.local/share/fonts, skipping any already present:
#   Inter                       — all UI text (bar, menus, notifications, titles, GTK)
#   JetBrains Mono              — terminal, calendar, shortcut sheet
#   JetBrainsMono Nerd Font     — the icon glyphs (Material Design, used like SF Symbols)
# Prefer your distro's packages when they exist (Debian/Ubuntu: fonts-inter fonts-jetbrains-mono;
# Arch: inter-font ttf-jetbrains-mono ttf-jetbrains-mono-nerd); the Nerd Font usually isn't packaged.
set -euo pipefail

FONTS="${XDG_DATA_HOME:-$HOME/.local/share}/fonts"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
have() { fc-list : family | grep -qiF "$1"; }
fetch() { curl -fsSL --retry 3 -o "$2" "$1"; }

if have "JetBrainsMono Nerd Font"; then
    echo "✓ JetBrainsMono Nerd Font"
else
    echo "→ JetBrainsMono Nerd Font"
    fetch https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.tar.xz "$TMP/nf.tar.xz"
    mkdir -p "$FONTS/JetBrainsMonoNerd"
    tar -xJf "$TMP/nf.tar.xz" -C "$FONTS/JetBrainsMonoNerd" --wildcards '*.ttf'
fi

if have "JetBrains Mono"; then
    echo "✓ JetBrains Mono"
else
    echo "→ JetBrains Mono"
    fetch https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip "$TMP/jbm.zip"
    mkdir -p "$FONTS/JetBrainsMono"
    (cd "$TMP" && unzip -qo jbm.zip 'fonts/ttf/*' && cp fonts/ttf/*.ttf "$FONTS/JetBrainsMono/")
fi

if have "Inter"; then
    echo "✓ Inter"
else
    echo "→ Inter"
    fetch https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip "$TMP/inter.zip"
    mkdir -p "$FONTS/Inter"
    (cd "$TMP" && unzip -qo inter.zip 'extras/otf/*' && cp extras/otf/*.otf "$FONTS/Inter/")
fi

fc-cache -f "$FONTS" >/dev/null
echo "✓ fonts ready"
