#!/bin/sh
# Example display layout hook. Copy to ~/.config/i3/local/monitors.sh, make it executable,
# and adjust. Harbor's autostart runs it first on every i3 start/restart (before the
# wallpaper is composed for the layout), so $mod+Shift+r picks up a monitor you just plugged in.
#
# Find your output names and modes with:  xrandr --query
#
# This example: a 4K panel run at 1440p as the primary screen, and a 1080p screen to its
# right with the bottom edges aligned (y = 1440 - 1080 = 360). Outputs that aren't connected
# (e.g. inside an xrdp or VNC session) are left alone.
PRIMARY=DP-0
SECOND=HDMI-0

q=$(xrandr --query)
printf '%s\n' "$q" | grep -q "^$PRIMARY connected" || exit 0

if printf '%s\n' "$q" | grep -q "^$SECOND connected"; then
    exec xrandr --output "$PRIMARY" --mode 2560x1440 --pos 0x0 --primary \
                --output "$SECOND"  --mode 1920x1080 --pos 2560x360
fi
exec xrandr --output "$PRIMARY" --mode 2560x1440 --pos 0x0 --primary --output "$SECOND" --off

# Pair it with workspace pins in ~/.config/i3/local/i3.conf:
#   workspace 1 output DP-0
#   workspace 6 output HDMI-0 DP-0
