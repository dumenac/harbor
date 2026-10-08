#!/usr/bin/env python3
"""Clipboard history — daemon + rofi script mode (launcher tab "Clipboard").

  clipboard.py daemon   watch the CLIPBOARD selection (XFixes events, no polling) and keep
                        the last 60 text entries. Started per display by autostart.sh.
  clipboard.py          (run by rofi) list the history, newest first; Enter copies an entry back.

Privacy: history lives in $XDG_RUNTIME_DIR (RAM, gone at reboot), mode 0600. Anything a password
manager marks as secret (x-kde-passwordManagerHint, used by KeePassXC & co.) is never recorded,
and neither is anything over 200 kB.
"""
import json
import os
import subprocess as sp
import sys
import time
from pathlib import Path

RUN = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "harbor"
HISTORY = RUN / "clipboard.json"
KEEP = 60
MAX_BYTES = 200_000


def load():
    try:
        return json.loads(HISTORY.read_text())
    except (OSError, ValueError):
        return []


def save(items):
    RUN.mkdir(parents=True, exist_ok=True)
    tmp = HISTORY.with_name(f".clipboard.{os.getpid()}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(items[:KEEP], f, ensure_ascii=False)
    os.replace(tmp, HISTORY)


def xclip_out(*args):
    try:
        return sp.run(["xclip", "-selection", "clipboard", "-o", *args], capture_output=True,
                      timeout=1.5).stdout
    except (OSError, sp.SubprocessError):
        return b""


def record():
    targets = xclip_out("-t", "TARGETS").decode(errors="replace").split()
    if "x-kde-passwordManagerHint" in targets:
        return
    if not any(t in targets for t in ("UTF8_STRING", "text/plain;charset=utf-8", "STRING", "TEXT", "text/plain")):
        return
    data = xclip_out()
    if not data or len(data) > MAX_BYTES:
        return
    text = data.decode("utf-8", errors="replace")
    if not text.strip():
        return
    items = [e for e in load() if e["text"] != text]
    save([{"text": text, "t": time.time()}] + items)


def daemon():
    try:
        Path("/proc/self/comm").write_text("harbor-clip")
    except OSError:
        pass
    from Xlib import X, display  # noqa: F401 — python3-xlib
    from Xlib.ext import xfixes
    d = display.Display()
    if not d.has_extension("XFIXES"):
        sys.exit("harbor-clip: no XFIXES")
    d.xfixes_query_version()
    root = d.screen().root
    clip = d.intern_atom("CLIPBOARD")
    d.xfixes_select_selection_input(root, clip, xfixes.XFixesSetSelectionOwnerNotifyMask)
    d.flush()   # python-xlib buffers requests; without this the subscription never reaches X
    while True:
        ev = d.next_event()
        # compare by name: python-xlib imports its extension modules twice, so isinstance fails
        if type(ev).__name__ == "SetSelectionOwnerNotify":
            time.sleep(0.05)   # let the new owner settle before asking it for data
            try:
                record()
            except Exception as e:  # noqa: BLE001 — never let one odd selection kill the daemon
                print(f"harbor-clip: {e}", file=sys.stderr)


def ago(t):
    s = time.time() - t
    return ("now" if s < 60 else f"{int(s // 60)} min" if s < 3600 else
            f"{int(s // 3600)} h" if s < 86400 else f"{int(s // 86400)} d")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def picker():
    retv, info = os.environ.get("ROFI_RETV"), os.environ.get("ROFI_INFO", "")
    if retv == "1" and info:
        if info == "clear":
            save([])
        else:
            items = load()
            i = int(info)
            if 0 <= i < len(items):
                sp.Popen(["xclip", "-selection", "clipboard"], stdin=sp.PIPE, stdout=sp.DEVNULL,
                         stderr=sp.DEVNULL, start_new_session=True).communicate(items[i]["text"].encode())
                sp.Popen(["notify-send", "-a", "clipboard", "-t", "1800", "-h",
                          "string:x-dunst-stack-tag:clipboard", "\U000F0A38  Copied"],
                         stdout=sp.DEVNULL, stderr=sp.DEVNULL, start_new_session=True)
        return
    out = sys.stdout
    out.write("\0markup-rows\x1ftrue\n\0no-custom\x1ftrue\n")
    items = load()
    if not items:
        out.write("\0message\x1fNothing copied yet — history lives in memory and clears at reboot\n")
        return
    out.write(f"\0message\x1f{len(items)} recent · Enter copies · kept in memory only\n")
    for i, e in enumerate(items):
        one = " ".join(e["text"].replace("\0", "").replace("\x1f", "").split())
        lines = e["text"].count("\n") + 1
        preview = esc(one[:96] + ("…" if len(one) > 96 else ""))
        extra = f"{ago(e['t'])}" + (f" · {lines} lines" if lines > 1 else "")
        out.write(f"{preview}   <span alpha='55%'>{extra}</span>\0info\x1f{i}\x1fmeta\x1f{esc(one[:400])}\n")
    out.write("<span alpha='55%'>\U000F0C62   Clear history</span>\0info\x1fclear\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        daemon()
    else:
        picker()
