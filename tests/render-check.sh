#!/usr/bin/env bash
# Install Harbor into a throwaway HOME, render both appearances, validate them with `i3 -C`,
# then uninstall and check the original files came back. Needs no X server.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
export HOME="$T" XDG_CONFIG_HOME="$T/.config" XDG_DATA_HOME="$T/.local/share"
unset DISPLAY

mkdir -p "$T/.config/i3"
echo "# someone's old config" > "$T/.config/i3/config"

"$REPO/install.sh" --yes --force > "$T/install.log" 2>&1 || { cat "$T/install.log"; exit 1; }
echo "✓ install into a clean HOME"
"$T/.config/i3/scripts/harbor" check
echo y | "$REPO/uninstall.sh" > "$T/uninstall.log" 2>&1 || { cat "$T/uninstall.log"; exit 1; }
grep -q "someone's old config" "$T/.config/i3/config" || { echo "✗ uninstall didn't restore the old config"; exit 1; }
echo "✓ uninstall restored the previous config"
