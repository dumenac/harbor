#!/usr/bin/env bash
# Print docs/keybindings.md from the live parse of config/i3/config (keys.py --print).
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/.config/i3"
cp "$REPO/config/i3/config" "$T/.config/i3/config"
echo "# Keyboard shortcuts"
echo
echo "Generated from \`config/i3/config\` by \`make keys\` — the same list \`\$mod+F1\` shows on screen."
echo "❖ Super · ⇧ Shift · ⌃ Ctrl · ⌥ Alt"
HOME="$T" python3 "$REPO/config/i3/scripts/keys.py" --print | awk '
    /^$/ { next }
    /^[^ ]/ { printf "\n## %s\n\n| Keys | Does |\n| --- | --- |\n", $0; next }
    { sub(/^  /, ""); k = substr($0, 1, 23); d = substr($0, 24); gsub(/ +$/, "", k);
      gsub(/</, "\\&lt;", k); gsub(/\|/, "\\|", k); gsub(/ \/ /, "</kbd> / <kbd>", k);
      printf "| <kbd>%s</kbd> | %s |\n", k, d }'
