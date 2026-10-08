#!/usr/bin/env python3
"""Emoji picker — a rofi script mode (launcher tab "Emoji").

Lists every fully-qualified emoji from Unicode's emoji-test.txt (unicode-data / unicode-emoji), recently
used first, searchable by name, group and subgroup. Enter copies it to the clipboard and types
it into the window you were in.
"""
import json
import os
import subprocess as sp
import sys
from pathlib import Path

SOURCES = [Path(p) for p in ("/usr/share/unicode/emoji/emoji-test.txt",          # Debian/Ubuntu: unicode-data
                              "/usr/share/unicode-emoji/emoji-test.txt",          # some distros
                              "/usr/share/unicode/emoji-test.txt")]
SOURCE = next((p for p in SOURCES if p.exists()), SOURCES[0])
CACHE = Path.home() / ".cache/harbor/emoji.json"
RECENT = Path.home() / ".local/state/harbor/emoji-recent.json"
KEEP_RECENT = 16


def catalogue():
    try:
        if CACHE.stat().st_mtime >= SOURCE.stat().st_mtime:
            return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        pass
    items, group, sub = [], "", ""
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
        elif line.startswith("# subgroup:"):
            sub = line.split(":", 1)[1].strip().replace("-", " ")
        elif "; fully-qualified" in line and "#" in line:
            rest = line.split("#", 1)[1].strip()          # "😀 E1.0 grinning face"
            char, _, name = rest.split(" ", 2)
            if ":" in name and "skin tone" in name:       # keep the list calm: no skin-tone variants
                continue
            items.append([char, name, f"{group} {sub}"])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(items, ensure_ascii=False))
    return items


def recent():
    try:
        return json.loads(RECENT.read_text())
    except (OSError, ValueError):
        return []


def remember(char):
    r = [c for c in recent() if c != char]
    RECENT.parent.mkdir(parents=True, exist_ok=True)
    RECENT.write_text(json.dumps([char] + r[:KEEP_RECENT - 1], ensure_ascii=False))


def emit(char, name, meta):
    sys.stdout.write(f"{char}   {name}\0info\x1f{char}\x1fmeta\x1f{meta}\n")


def main():
    if os.environ.get("ROFI_RETV") == "1" and os.environ.get("ROFI_INFO"):
        char = os.environ["ROFI_INFO"]
        remember(char)
        sp.Popen(["xclip", "-selection", "clipboard"], stdin=sp.PIPE, stdout=sp.DEVNULL,
                 stderr=sp.DEVNULL, start_new_session=True).communicate(char.encode())
        # type it into the window that had focus once rofi has closed
        sp.Popen(["sh", "-c", 'sleep 0.25; xdotool type --clearmodifiers -- "$1"', "sh", char],
                 stdin=sp.DEVNULL, stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
        return  # printing nothing closes rofi
    if not SOURCE.exists():
        sys.stdout.write("\0message\x1fInstall Unicode's emoji list (Debian/Ubuntu: unicode-data, Arch: unicode-emoji)\n")
        return
    sys.stdout.write("\0no-custom\x1ftrue\n\0message\x1fEnter copies and types it · recent first\n")
    items = catalogue()
    by_char = {c: (n, m) for c, n, m in items}
    seen = set()
    for c in recent():
        if c in by_char:
            emit(c, by_char[c][0], "recent " + by_char[c][1])
            seen.add(c)
    for c, n, m in items:
        if c not in seen:
            emit(c, n, m)


if __name__ == "__main__":
    main()
