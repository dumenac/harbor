#!/usr/bin/env python3
"""harbor-bar — the i3bar status line of the Harbor design system.

Quiet by default, like a menu bar: now playing · status icons · Control Center · clock.
System stats appear on their own only when something needs attention (hot CPU, low
memory or disk), or always if "System Stats in Bar" is on in the Control Center.

Event driven: clicks from i3bar, `playerctl --follow`, `pactl subscribe`, SIGUSR1 (sent by
volume.sh / caffeine.sh / harbor) and a 2 s tick. Colours come from ~/.cache/harbor/theme.json,
re-read whenever harbor rewrites it.

Clicks:  clock → calendar (right: toggle stats) · control icon → Control Center · Focus → menu
         volume → mute, scroll ±5 %, right → pavucontrol · network → details
         now playing → play/pause, right → next · dnd / caffeine / night shift → turn off
"""
import json
import os
import re
import selectors
import signal
import subprocess as sp
import sys
import time
from collections import deque
from pathlib import Path

HOME = Path.home()
SCRIPTS = HOME / ".config/i3/scripts"
HARBOR = str(SCRIPTS / "harbor")
THEME = HOME / ".cache/harbor/theme.json"
XRUN = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
RUN = XRUN / "harbor"
DISPLAY = os.environ.get("DISPLAY", ":0")

ICON = {
    "focus": "\U000F117B", "music": "\U000F075A", "pause": "\U000F03E4", "dnd": "\U000F009B", "coffee": "\U000F0176",
    "nightshift": "\U000F0594", "control": "\U000F1542",
    "wifi": ["\U000F092F", "\U000F091F", "\U000F0922", "\U000F0925", "\U000F0928"], "wifi_off": "\U000F092E",
    "ethernet": "\U000F0200", "vol_mute": "\U000F075F", "vol": ["\U000F057F", "\U000F0580", "\U000F057E"],
    "cpu": "\U000F0EE0", "temp": "\U000F050F", "mem": "\U000F035B", "disk": "\U000F02CA",
}
DEFAULT_PALETTE = {"text": "#ecedee", "text_muted": "#9da3ab", "text_faint": "#6b727b",
                   "accent": "#e8a94a", "warning": "#f5b94f", "danger": "#ff6b5e"}


def sh(*cmd, timeout=1.0):
    try:
        return sp.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, sp.SubprocessError):
        return ""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ic(glyph):
    """An icon, one size step above the text — the way SF Symbols sit beside a label."""
    return f"<span font_family='JetBrainsMono Nerd Font Propo' size='large' rise='-1024'>{glyph}</span>"


class Bar:
    def __init__(self):
        self.pal, self.theme_mtime = dict(DEFAULT_PALETTE), 0
        self.cpu_prev, self.cpu_hist = None, deque(maxlen=5)
        self.cpu = 0.0
        self.temp_path = self.find_temp()
        self.vol, self.vol_flash_until = None, 0.0
        self.player = None
        self.dnd, self.dnd_checked = False, 0.0
        self.ssid, self.ssid_checked = None, 0.0
        self.wifi_q, self.wifi_level = None, None
        self.children = []
        self.last_line = None
        self.sel = selectors.DefaultSelector()
        self.procs = {}
        self.wake_r, self.wake_w = os.pipe()
        os.set_blocking(self.wake_w, False)
        signal.set_wakeup_fd(self.wake_w)
        signal.signal(signal.SIGUSR1, lambda *_: None)
        self.sel.register(self.wake_r, selectors.EVENT_READ, "wake")
        self.bufs = {}
        os.set_blocking(0, False)
        self.sel.register(0, selectors.EVENT_READ, "clicks")

    # ── helpers ──────────────────────────────────────────────────────────────────────
    def spawn(self, *cmd):
        try:
            self.children.append(sp.Popen(cmd, stdin=sp.DEVNULL, stdout=sp.DEVNULL,
                                          stderr=sp.DEVNULL, start_new_session=True))
        except OSError:
            pass

    def reap(self):
        self.children = [c for c in self.children if c.poll() is None]

    def start_follower(self, key, cmd):
        try:
            p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.DEVNULL, stdin=sp.DEVNULL)
        except OSError:
            return
        os.set_blocking(p.stdout.fileno(), False)
        self.sel.register(p.stdout.fileno(), selectors.EVENT_READ, key)
        self.bufs[key] = ""
        self.procs[key] = {"proc": p, "fd": p.stdout.fileno(), "since": time.monotonic()}

    def restart_dead_followers(self):
        specs = {
            "player": ["playerctl", "--follow", "metadata", "--format", "{{status}}\t{{artist}}\t{{title}}"],
            "audio": ["pactl", "subscribe"],
        }
        for key, cmd in specs.items():
            info = self.procs.get(key)
            if info and info["proc"].poll() is None:
                continue
            if info and not info.get("closed"):
                self.unregister(info["fd"])
                info["proc"].stdout.close()
                info["closed"] = True
                if key == "player":
                    self.player = None
            if info and time.monotonic() - info["since"] < 10:   # back off a crash-looping helper
                continue
            self.start_follower(key, cmd)

    def load_theme(self):
        try:
            m = THEME.stat().st_mtime_ns
        except OSError:
            return
        if m == self.theme_mtime:
            return
        try:
            self.pal = {**DEFAULT_PALETTE, **json.loads(THEME.read_text())["palette"]}
            self.theme_mtime = m
        except (OSError, ValueError, KeyError):
            pass

    # ── data ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def find_temp():
        for name_file in Path("/sys/class/hwmon").glob("hwmon*/name"):
            try:
                if name_file.read_text().strip() in ("k10temp", "zenpower", "coretemp"):
                    t = name_file.parent / "temp1_input"
                    if t.exists():
                        return t
            except OSError:
                continue
        return None

    def sample_cpu(self):
        try:
            f = [int(x) for x in Path("/proc/stat").read_text().split("\n", 1)[0].split()[1:]]
        except (OSError, ValueError):
            return
        idle, total = f[3] + f[4], sum(f[:8])
        if self.cpu_prev:
            di, dt_ = idle - self.cpu_prev[0], total - self.cpu_prev[1]
            if dt_ > 0:
                self.cpu = 100.0 * (1 - di / dt_)
                self.cpu_hist.append(self.cpu)
        self.cpu_prev = (idle, total)

    def temp(self):
        try:
            return int(self.temp_path.read_text()) / 1000 if self.temp_path else None
        except (OSError, ValueError):
            return None

    @staticmethod
    def mem():
        info = {}
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0]) * 1024
        except (OSError, ValueError):
            return None
        return info.get("MemTotal", 0), info.get("MemAvailable", 0)

    @staticmethod
    def disk():
        try:
            s = os.statvfs("/")
        except OSError:
            return None
        return s.f_blocks * s.f_frsize, s.f_bavail * s.f_frsize

    def read_volume(self):
        raw = sh("wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@")
        m = re.search(r"Volume:\s*([\d.]+)", raw)
        new = (round(float(m.group(1)) * 100), "MUTED" in raw) if m else None
        if self.vol is not None and new != self.vol:
            self.vol_flash_until = time.monotonic() + 2.5
        self.vol = new

    def refresh_dnd(self, force=False):
        if force or time.monotonic() - self.dnd_checked > 5:
            self.dnd = sh("dunstctl", "is-paused").strip() == "true"
            self.dnd_checked = time.monotonic()

    @staticmethod
    def net():
        wifi, wired = None, False
        for d in Path("/sys/class/net").iterdir():
            try:
                if (d / "wireless").exists():
                    if (d / "operstate").read_text().strip() == "up":
                        wifi = d.name
                elif (d / "device").exists() and (d / "carrier").read_text().strip() == "1":
                    wired = True
            except OSError:
                continue
        quality = None
        if wifi:
            try:
                for line in Path("/proc/net/wireless").read_text().splitlines()[2:]:
                    if line.strip().startswith(wifi + ":"):
                        quality = float(line.split()[2].rstrip("."))
            except (OSError, ValueError, IndexError):
                pass
        return wifi, quality, wired

    def wifi_bars(self, q):
        """0–4 bars from link quality (/70), smoothed with hysteresis so it doesn't flicker."""
        if q is None:
            return 0
        self.wifi_q = q if self.wifi_q is None else 0.7 * self.wifi_q + 0.3 * q
        exact = self.wifi_q / 70 * 4 + 0.5          # 1 bar ≥ 0 %, 4 bars ≥ ~70 %
        lvl = self.wifi_level
        if lvl is None or abs(exact - (lvl + 0.5)) > 0.75:
            lvl = int(exact)
        self.wifi_level = max(1, min(4, lvl))
        return self.wifi_level

    def wifi_name(self, iface):
        if time.monotonic() - self.ssid_checked > 30:
            self.ssid = sh("nmcli", "-t", "-g", "GENERAL.CONNECTION", "device", "show", iface).strip() or None
            self.ssid_checked = time.monotonic()
        return self.ssid

    # ── render ───────────────────────────────────────────────────────────────────────
    def block(self, name, text, color=None, gap=16, **kw):
        b = {"name": name, "full_text": text, "markup": "pango", "separator": False,
             "separator_block_width": gap, "color": color or self.pal["text"]}
        b.update(kw)
        return b

    @staticmethod
    def focus():
        """Minutes left in a Focus session (None = open-ended), or False when not focusing."""
        try:
            s = json.loads((RUN / f"focus{DISPLAY}.json").read_text())
        except (OSError, ValueError):
            return False
        until = s.get("until")
        if until is None:
            return None
        left = until - time.time()
        return False if left <= 0 else int(-(-left // 60))

    def blocks(self):
        P = self.pal
        focus = self.focus()
        stats = (RUN / "stats").exists() and focus is False   # Focus hides the optional extras
        out = []

        # Focus: a quiet countdown in the accent; click for End / +15 min
        if focus is not False:
            label = "Focus" if focus is None else f"Focus · {focus} min"
            out.append(self.block("focus", f"{ic(ICON['focus'])}  {label}", P["accent"], gap=22))

        # now playing (hidden during Focus)
        if self.player and focus is False:
            status, artist, title = self.player
            text = f"{title} — {artist}" if artist else title
            if len(text) > 52:
                text = text[:51].rstrip() + "…"
            playing = status == "Playing"
            out.append(self.block("player", f"{ic(ICON['music'] if playing else ICON['pause'])}  {esc(text)}",
                                  P["text_muted"] if playing else P["text_faint"], gap=22))

        # system: shown when asked for, or when something is wrong
        avg = sum(self.cpu_hist) / len(self.cpu_hist) if self.cpu_hist else 0
        t = self.temp()
        mem = self.mem()
        dsk = self.disk()
        items = []
        if stats or avg >= 90:
            items.append(("cpu", f"{ic(ICON['cpu'])} {self.cpu:.0f}%", P["warning"] if avg >= 90 else None))
        if t is not None and (stats or t >= 85):
            items.append(("temp", f"{ic(ICON['temp'])} {t:.0f}°",
                          P["danger"] if t >= 95 else P["warning"] if t >= 85 else None))
        if mem and mem[0]:
            free = mem[1] / mem[0]
            if stats or free < 0.10:
                used = (mem[0] - mem[1]) / 2**30
                items.append(("mem", f"{ic(ICON['mem'])} {used:.1f} GB",
                              P["danger"] if free < 0.05 else P["warning"] if free < 0.10 else None))
        if dsk and dsk[0]:
            free = dsk[1] / dsk[0]
            if stats or free < 0.10:
                items.append(("disk", f"{ic(ICON['disk'])} {dsk[1] / 2**30:.0f} GB free",
                              P["danger"] if free < 0.05 else P["warning"] if free < 0.10 else None))
        for i, (name, text, col) in enumerate(items):
            out.append(self.block(name, f"<span font_features='tnum'>{text}</span>",
                                  col or P["text_muted"], gap=22 if i == len(items) - 1 else 14))

        # status toggles — only visible while on
        self.refresh_dnd()
        if self.dnd and focus is False:      # Focus already says notifications are paused
            out.append(self.block("dnd", ic(ICON["dnd"]), P["accent"], gap=14))
        if (XRUN / "caffeine.on").exists():
            out.append(self.block("caffeine", ic(ICON["coffee"]), P["accent"], gap=14))
        if (RUN / f"nightshift{DISPLAY}").exists():
            out.append(self.block("nightshift", ic(ICON["nightshift"]), P["accent"], gap=14))

        # network
        wifi, q, wired = self.net()
        if wired:
            out.append(self.block("net", ic(ICON["ethernet"]), gap=14))
        elif wifi:
            text = ic(ICON["wifi"][self.wifi_bars(q)])
            if stats:
                name = self.wifi_name(wifi)
                text += f"  <span foreground='{P['text_muted']}'>{esc(name)}</span>" if name else ""
            out.append(self.block("net", text, gap=14))
        else:
            out.append(self.block("net", ic(ICON["wifi_off"]), P["danger"], gap=14))

        # volume
        if self.vol:
            pct, muted = self.vol
            if muted:
                text, col = ic(ICON["vol_mute"]), P["text_faint"]
            else:
                text, col = ic(ICON["vol"][0 if pct < 34 else 1 if pct < 67 else 2]), None
            if stats or time.monotonic() < self.vol_flash_until:
                text += f" <span font_features='tnum' foreground='{P['text_muted']}'>{pct}%</span>"
            out.append(self.block("volume", text, col, gap=14))

        # control center + clock
        out.append(self.block("control", ic(ICON["control"]), gap=16))
        now = time.localtime()
        out.append(self.block(
            "clock",
            f"<span foreground='{P['text_muted']}'>{time.strftime('%a %-d %b', now)}</span>  "
            f"<span font_features='tnum'>{time.strftime('%H:%M', now)}</span>",
            gap=10))
        return out

    def emit(self):
        line = json.dumps(self.blocks(), ensure_ascii=False)
        if line != self.last_line:
            sys.stdout.write(line + ",\n")
            sys.stdout.flush()
            self.last_line = line

    # ── input ────────────────────────────────────────────────────────────────────────
    def on_click(self, ev):
        name, button = ev.get("name"), ev.get("button")
        if name == "clock":
            if button == 1:
                self.spawn(HARBOR, "calendar")
            elif button == 3:
                self.spawn(HARBOR, "stats", "toggle")
        elif name == "control" and button in (1, 3):
            self.spawn(HARBOR, "center")
        elif name == "volume":
            if button == 1:
                sh("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")
            elif button == 3:
                self.spawn("pavucontrol")
            elif button == 4:
                sh("wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+")
            elif button == 5:
                sh("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-")
            self.read_volume()
        elif name == "player":
            if button == 1:
                self.spawn("playerctl", "play-pause")
            elif button == 3:
                self.spawn("playerctl", "next")
        elif name == "net" and button == 1:
            self.spawn(sys.executable, os.path.abspath(__file__), "--net-details")
        elif name == "focus" and button in (1, 3):
            self.spawn(HARBOR, "focus", "menu")
        elif name in ("dnd", "caffeine", "nightshift") and button == 1:
            self.spawn(HARBOR, name, "off")
        elif name in ("cpu", "temp", "mem", "disk") and button == 1:
            self.spawn("kitty", "--class", "floating-term", "-e", "btop" if sh("which", "btop") else "top")

    def unregister(self, fd):
        try:
            self.sel.unregister(fd)
        except (KeyError, ValueError):
            pass

    def read_lines(self, fd, key):
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            return []
        except OSError:
            chunk = b""
        if not chunk:                       # EOF
            if key == "clicks":             # i3bar went away
                sys.exit(0)
            self.unregister(fd)             # helper exited; restarted on the next tick
            return []
        *lines, self.bufs[key] = (self.bufs.get(key, "") + chunk.decode(errors="replace")).split("\n")
        return lines

    def run(self):
        sys.stdout.write(json.dumps({"version": 1, "click_events": True}) + "\n[\n")
        sys.stdout.flush()
        self.load_theme()
        self.restart_dead_followers()
        self.sample_cpu()
        self.read_volume()
        self.refresh_dnd(force=True)
        self.emit()
        next_tick = time.monotonic()
        while True:
            now = time.monotonic()
            # tick every 2 s, and right on the minute so the clock never lags
            to_minute = 60 - time.time() % 60 + 0.05
            timeout = max(0.0, min(next_tick - now, to_minute))
            for key, _ in self.sel.select(timeout):
                k = key.data
                if k == "wake":
                    try:
                        os.read(self.wake_r, 512)
                    except BlockingIOError:
                        pass
                    self.read_volume()
                    self.refresh_dnd(force=True)
                elif k == "clicks":
                    for line in self.read_lines(0, "clicks"):
                        line = line.strip().lstrip(",").strip()
                        if line.startswith("{"):
                            try:
                                self.on_click(json.loads(line))
                            except ValueError:
                                pass
                elif k == "player":
                    for line in self.read_lines(key.fd, "player"):
                        parts = line.split("\t")
                        self.player = (tuple(parts) if len(parts) == 3 and parts[0] in ("Playing", "Paused")
                                       and parts[2] else None)
                elif k == "audio":
                    if any(("sink" in ln or "server" in ln) and "input" not in ln
                           for ln in self.read_lines(key.fd, "audio")):
                        self.read_volume()
            if time.monotonic() >= next_tick:
                next_tick = time.monotonic() + 2
                self.sample_cpu()
                self.reap()
                self.restart_dead_followers()
            self.load_theme()
            self.emit()


def net_details():
    lines = []
    for d in sorted(Path("/sys/class/net").iterdir()):
        try:
            if (d / "operstate").read_text().strip() != "up" and d.name != "tailscale0":
                continue
        except OSError:
            continue
        if not ((d / "device").exists() or d.name == "tailscale0"):
            continue
        addr = sh("ip", "-4", "-br", "addr", "show", d.name).split()
        ip = addr[2].split("/")[0] if len(addr) > 2 else "no IPv4"
        if (d / "wireless").exists():
            ssid = sh("nmcli", "-t", "-g", "GENERAL.CONNECTION", "device", "show", d.name).strip()
            label = f"Wi-Fi  <b>{esc(ssid or d.name)}</b>"
        elif d.name == "tailscale0":
            label = "Tailscale"
        else:
            label = f"Ethernet  {d.name}"
        lines.append(f"{label}\n<span alpha='65%'>{ip}</span>")
    sp.run(["notify-send", "-a", "network", "-h", "string:x-dunst-stack-tag:network",
            "\U000F0928  Network", "\n".join(lines) or "Offline"])


if __name__ == "__main__":
    if "--net-details" in sys.argv:
        net_details()
        sys.exit(0)
    try:
        Path("/proc/self/comm").write_text("harbor-bar")
    except OSError:
        pass
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    Bar().run()
