#!/bin/sh
# Keep Awake: on = no screensaver, no DPMS, no auto-lock. The state file is read by the bar
# (shows a cup) and by the Control Center.
state="${XDG_RUNTIME_DIR:-/tmp}/caffeine.on"

action="${1:-toggle}"
if [ "$action" = toggle ]; then
    if [ -e "$state" ]; then action=off; else action=on; fi
fi

case "$action" in
    on)
        xset s off -dpms
        touch "$state"
        notify-send -a caffeine -h string:x-dunst-stack-tag:caffeine "󰅶  Keep Awake on" "The screen won't sleep or lock"
        ;;
    off)
        xset s on +dpms
        rm -f "$state"
        notify-send -a caffeine -h string:x-dunst-stack-tag:caffeine "󰛊  Keep Awake off" "Normal sleep and lock"
        ;;
    status)
        if [ -e "$state" ]; then echo on; else echo off; fi
        exit 0
        ;;
    *)
        echo "usage: $0 [on|off|toggle|status]" >&2
        exit 2
        ;;
esac
pkill -USR1 -x harbor-bar 2>/dev/null
exit 0
