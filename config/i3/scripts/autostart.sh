#!/bin/sh
# Harbor session autostart. Wired to `exec_always`: runs at startup and on every restart
# ($mod+Shift+r) — NOT on reload. Idempotent: a daemon is started only if no instance is already
# running on *this* DISPLAY, so several X sessions (local + xrdp/VNC) can share one user.
#
# Local hooks (optional, never touched by the installer):
#   ~/.config/i3/local/monitors.sh    run first — set up your outputs with xrandr
#   ~/.config/i3/local/autostart.sh   run last  — start your own things
S="$HOME/.config/i3/scripts"
L="$HOME/.config/i3/local"
up() {
    for pid in $(pgrep -x "$1"); do
        if tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -qx "DISPLAY=$DISPLAY"; then
            return 0
        fi
    done
    return 1
}

# ── Displays: your layout if you have one, else make the first connected output primary (tray)
if [ -x "$L/monitors.sh" ]; then
    "$L/monitors.sh"
elif ! xrandr --query | grep -q ' connected primary'; then
    out=$(xrandr --query | awk '/ connected/ {print $1; exit}')
    [ -n "$out" ] && xrandr --output "$out" --primary
fi

# ── Harbor: render Day/Night for the current time (wallpaper, i3/bar/rofi/dunst/kitty/GTK colours),
# then keep watching the clock for the switch and the Focus timer.
"$S/harbor" apply
up harbor-watch || "$S/harbor" watch &

# ── Compositor — only where there is a GPU: xorgxrdp (:10+) and Xvnc (VNC-* outputs) have no GL.
# Without picom everything still works; you lose blur, shadows, corners and motion.
case "$DISPLAY" in
    :1[0-9]*) ;;
    *) xrandr --query | grep -q '^VNC-' || up picom || picom -b ;;
esac

# ── Daemons
up dunst      || dunst &
up xsettingsd || { command -v xsettingsd >/dev/null && xsettingsd & }
up harbor-clip || "$S/clipboard.py" daemon &
# The screen locker and polkit agent need a logind session (a VNC user unit has none; a polkit
# agent there would claim the session of your real desktop).
if [ -n "$XDG_SESSION_ID" ]; then
    up xss-lock || xss-lock --transfer-sleep-lock -- "$S/lock.sh" &
    up lxpolkit || { command -v lxpolkit >/dev/null && lxpolkit & }
fi
up flameshot || { command -v flameshot >/dev/null && flameshot & }
if command -v blueman-applet >/dev/null && systemctl is-active -q bluetooth 2>/dev/null; then
    up blueman-applet || blueman-applet &
fi
if command -v nm-applet >/dev/null && systemctl is-active -q NetworkManager 2>/dev/null; then
    up nm-applet || nm-applet &
fi

# Keep Awake survives i3 restarts
[ -e "${XDG_RUNTIME_DIR:-/tmp}/caffeine.on" ] && xset s off -dpms

# Hello — once per X server, after dunst is up
(sleep 2; "$S/harbor" greet) &

# ── XDG autostart entries (/etc/xdg/autostart, ~/.config/autostart) — once per X server, not on
# every i3 restart. The marker is a root-window property: it survives i3 restarts and dies with
# the X server, so a fresh login runs it again.
if command -v dex >/dev/null && ! xprop -root I3_DEX_DONE 2>/dev/null | grep -q '= 1'; then
    xprop -root -f I3_DEX_DONE 32c -set I3_DEX_DONE 1
    dex --autostart --environment i3 &
fi

# ── Yours
[ -x "$L/autostart.sh" ] && "$L/autostart.sh" &
exit 0
