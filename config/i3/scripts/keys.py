#!/usr/bin/env python3
"""Keyboard Shortcuts — every bindsym in the i3 config, in plain English, searchable in rofi.

Reads ~/.config/i3/config live, so it never goes stale. Sections come from the config's
"# ── Name ──" headers; keys are drawn Mac-style (❖ Super, ⇧ Shift, ⌃ Ctrl, ⌥ Alt); runs of
similar bindings collapse into one row ("❖ 1 … 0  Go to workspace").

  keys.py           show in rofi ($mod+F1, Control Center → Keyboard Shortcuts)
  keys.py --print   plain text to stdout
"""
import re
import subprocess as sp
import sys
from pathlib import Path

CONFIG = Path.home() / ".config/i3/config"

MODS = {"Mod4": "❖", "Mod1": "⌥", "Shift": "⇧", "Ctrl": "⌃", "Control": "⌃"}
MOD_ORDER = "⌃⌥⇧❖"
KEYS = {
    "Return": "↵", "Tab": "⇥", "grave": "`", "space": "Space", "minus": "-", "plus": "+", "equal": "=",
    "bracketleft": "[", "bracketright": "]", "comma": ",", "period": ".", "semicolon": ";",
    "Left": "←", "Right": "→", "Up": "↑", "Down": "↓", "Escape": "⎋", "Print": "PrtSc",
    "XF86AudioRaiseVolume": "Vol+", "XF86AudioLowerVolume": "Vol−", "XF86AudioMute": "Mute",
    "XF86AudioMicMute": "Mic", "XF86AudioPlay": "Play", "XF86AudioPause": "Pause",
    "XF86AudioNext": "Next", "XF86AudioPrev": "Prev", "XF86AudioStop": "Stop",
}
ARROWS, VIM = ["Left", "Down", "Up", "Right"], ["j", "k", "l", "semicolon"]

# command → description, first match wins. {n} = workspace number, {dir} = direction word.
RULES = [
    (r"^exec \$term --class floating-term$", "Floating terminal"),
    (r"^exec \$term$", "Terminal"),
    (r"dropdown\.sh", "Drop-down terminal"),
    (r"launcher(?: apps)?$", "Launcher — apps, calculator, emoji, clipboard"),
    (r"launcher calc", "Calculator"), (r"launcher emoji", "Emoji"),
    (r"launcher clipboard", "Clipboard history"), (r"launcher windows", "Switch window"),
    (r"launcher run", "Run a command"),
    (r"^exec \$browser", "Firefox"), (r"^exec \$files", "Files"),
    (r"pavucontrol", "Sound settings"), (r"geeqie", "Photos (Geeqie)"),
    (r"keys\.py", "This list"), (r"lock\.sh", "Lock screen"),
    (r"harbor center", "Control Center"), (r"harbor toggle", "Light ⇄ Dark"),
    (r"harbor set auto", "Appearance back to Auto"), (r"harbor calendar", "Calendar"),
    (r"harbor dnd", "Do Not Disturb"), (r"harbor focus", "Focus"), (r"harbor power", "Power menu"),
    (r"screenshot\.sh gui", "Screenshot — select & annotate"),
    (r"screenshot\.sh full", "Screenshot — everything"),
    (r"screenshot\.sh window", "Screenshot — this window"),
    (r"screenshot\.sh area", "Screenshot — area to file"),
    (r"volume\.sh up", "Volume up"), (r"volume\.sh down", "Volume down"),
    (r"volume\.sh mute", "Mute"), (r"volume\.sh mic", "Microphone on / off"),
    (r"playerctl play-pause", "Play / pause"), (r"playerctl next", "Next track"),
    (r"playerctl previous", "Previous track"), (r"playerctl stop", "Stop"),
    (r"caffeine\.sh toggle", "Keep Awake"), (r"caffeine\.sh off", "Keep Awake off"),
    (r"dunstctl close-all", "Dismiss all notifications"), (r"dunstctl close", "Dismiss notification"),
    (r"dunstctl history-pop", "Bring back last notification"),
    (r"^kill$", "Close window"),
    (r"^\[urgent=latest\] focus", "Jump to the window asking for attention"),
    (r"^focus output \{dir\}$", "Focus the monitor"),
    (r"^focus \{dir\}$", "Focus window"),
    (r"^move container to output \{dir\}", "Move window to the monitor"),
    (r"^move workspace to output \{dir\}", "Move workspace to the monitor"),
    (r"^move \{dir\}$", "Move window"),
    (r"^resize ", "Resize window"),
    (r"^split h$", "Next window opens beside"), (r"^split v$", "Next window opens below"),
    (r"^fullscreen toggle global$", "Fullscreen across monitors"), (r"^fullscreen toggle$", "Fullscreen"),
    (r"^layout stacking$", "Stacked layout"), (r"^layout tabbed$", "Tabbed layout"),
    (r"^layout toggle split$", "Split layout / flip direction"),
    (r"^floating toggle$", "Float / tile window"), (r"^focus mode_toggle$", "Focus floating ⇄ tiled"),
    (r"^focus parent$", "Select parent container"), (r"^focus child$", "Select child container"),
    (r"^sticky toggle$", "Keep window on every workspace"), (r"^border toggle", "Window border style"),
    (r"^scratchpad show$", "Show / hide scratchpad"), (r"^move scratchpad$", "Send window to scratchpad"),
    (r"^move container to workspace number \{n\}; workspace number \{n\}$", "Move window there and follow"),
    (r"^move container to workspace number \{n\}$", "Move window to workspace"),
    (r"^workspace number \{n\}$", "Go to workspace"),
    (r"^workspace back_and_forth$", "Previous workspace"),
    (r"^workspace prev$", "Workspace to the left"), (r"^workspace next$", "Workspace to the right"),
    (r"^move container to workspace prev", "Move window a workspace left"),
    (r"^move container to workspace next", "Move window a workspace right"),
    (r"^reload$", "Reload i3 config"), (r"^restart$", "Restart i3 (keeps windows)"),
    (r"^bar mode toggle$", "Hide / show the bar"),
    (r"^mode \$mode_resize$", "Resize mode"), (r"^mode \$mode_gaps$", "Gaps mode"),
]


def config_lines():
    """The main config, then ~/.config/i3/local/*.conf (your additions) under their own heading."""
    yield from CONFIG.read_text().splitlines()
    for extra in sorted((CONFIG.parent / "local").glob("*.conf")):
        yield "# ── Yours ──"
        yield from extra.read_text().splitlines()


def parse():
    vars_, rows, section, depth = {}, [], "General", 0
    for raw in config_lines():
        line = raw.strip()
        m = re.match(r"^#\s*[─═]+\s*(.+?)\s*[─═]*$", line)
        if m and depth == 0:
            name = re.sub(r"[─═]+", "", m.group(1)).split(":")[0].strip()
            if name and not name.lower().startswith(("bar", "modes", "window rules")):
                section = name.split("(")[0].strip()
            continue
        if line.endswith("{"):
            depth += 1
        if line == "}":
            depth = max(0, depth - 1)
        m = re.match(r"^set\s+(\$\w+)\s+(.+)$", line)
        if m:
            vars_[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^bindsym\s+(?:--\S+\s+)*(\S+)\s+(.+)$", line)
        if m and depth == 0:
            rows.append((section, m.group(1), m.group(2)))
    return vars_, rows


def split_key(key, vars_):
    for v, val in vars_.items():
        key = key.replace(v, val)
    parts = key.split("+")
    mods = "".join(sorted((MODS.get(p, p) for p in parts[:-1]), key=MOD_ORDER.find))
    return mods, parts[-1]


def describe(cmd, vars_):
    cmd = " ".join(cmd.split())
    for v in ("$menu", "$scripts", "$harbor"):          # expand the helper paths, keep $term etc.
        if v in vars_:
            cmd = cmd.replace(v, vars_[v])
    if cmd.startswith("exec"):
        c = re.sub(r"^exec\s+(--no-startup-id\s+)?", "exec ", cmd)
    else:
        c = re.sub(r"\b(left|down|up|right)\b", "{dir}", cmd)
    c = re.sub(r"(workspace number) \$ws\d+", r"\1 {n}", c)
    for pat, text in RULES:
        if re.search(pat, c):
            return text
    return cmd


def rows():
    vars_, binds = parse()
    groups = {}
    for section, key, cmd in binds:
        mods, sym = split_key(key, vars_)
        cls = "digit" if sym.isdigit() else "arrow" if sym in ARROWS else "vim" if sym in VIM else sym
        desc = describe(cmd, vars_)
        if cmd.strip().startswith("resize") and cls in ("arrow", "vim"):
            desc = "Resize window"
        g = groups.setdefault((section, mods, desc), {"section": section, "mods": mods, "desc": desc, "keys": []})
        g["keys"].append((cls, sym))
    out = []
    for g in groups.values():
        classes = {c for c, _ in g["keys"]}
        parts = []
        if "digit" in classes:
            parts.append("1…0")
        if "arrow" in classes:   # only the arrows actually bound, in ←↓↑→ order
            parts.append("".join(KEYS[a] for a in ARROWS if ("arrow", a) in g["keys"]))
        if "vim" in classes:
            parts.append("".join({"semicolon": ";"}.get(v, v.upper()) for v in VIM if ("vim", v) in g["keys"]))
        for c, sym in g["keys"]:
            if c not in ("digit", "arrow", "vim"):
                k = KEYS.get(sym, sym.upper() if len(sym) == 1 else sym)
                if k not in parts:
                    parts.append(k)
        keys = " / ".join(f"{g['mods']}{p}" for p in parts)
        out.append((g["section"], keys, g["desc"]))
    return out


def main():
    data = rows()
    if "--print" in sys.argv:
        last = None
        for section, keys, desc in data:
            if section != last:
                print(f"\n{section}")
                last = section
            print(f"  {keys:<22} {desc}")
        return
    width = max(len(k) for _, k, _ in data) + 2
    lines = []
    for section, keys, desc in data:
        k = keys.replace("&", "&amp;").replace("<", "&lt;")
        lines.append(f"<span font_family='JetBrains Mono, DejaVu Sans Mono'>{k:<{width}}</span>"
                     f"{desc}   <span alpha='45%' size='small'>{section}</span>")
    theme = ("window { width: 980px; y-offset: 12%; } listview { lines: 16; } "
             "mainbox { children: [ inputbar, message, listview ]; } element-icon { enabled: false; }")
    sp.run(["rofi", "-dmenu", "-i", "-markup-rows", "-no-custom", "-p", "",
            "-mesg", f"<b>Keyboard Shortcuts</b>   <span alpha='55%'>{len(data)} · ❖ Super  ⇧ Shift  ⌃ Ctrl  ⌥ Alt · type to search</span>",
            "-theme-str", theme], input="\n".join(lines), text=True, stdout=sp.DEVNULL)


if __name__ == "__main__":
    main()
