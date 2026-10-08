#!/bin/sh
# screenshot.sh gui|full|window|area — saved to ~/Pictures/Screenshots and copied to the clipboard
dir="$HOME/Pictures/Screenshots"
mkdir -p "$dir"
file="$dir/$(date +%Y-%m-%d_%H-%M-%S).png"

case "${1:-gui}" in
    gui)
        # flameshot allows one instance per *user*, not per display: `flameshot gui` is
        # forwarded to whichever display started the daemon first (e.g. a local session plus an
        # xrdp/VNC one). Make the daemon belong to this display before asking for the GUI.
        for pid in $(pgrep -x -u "$(id -u)" flameshot); do
            tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep -qx "DISPLAY=$DISPLAY" && continue
            kill "$pid" 2>/dev/null || continue
            i=0; while [ "$i" -lt 20 ] && kill -0 "$pid" 2>/dev/null; do sleep 0.1; i=$((i+1)); done
        done
        exec flameshot gui -p "$dir" ;;
    full)   maim -u "$file" ;;
    window) maim -u -i "$(xdotool getactivewindow)" "$file" ;;
    area)
        # selection outline in the current Harbor accent (theme.json is written by harbor)
        rgb=$(jq -r '.palette.accent' "$HOME/.cache/harbor/theme.json" 2>/dev/null |
              awk '/^#[0-9a-fA-F]{6}$/ { printf "%.3f,%.3f,%.3f", strtonum("0x" substr($0,2,2))/255,
                                          strtonum("0x" substr($0,4,2))/255, strtonum("0x" substr($0,6,2))/255 }')
        maim -u -s -b 2 -c "${rgb:-0.18,0.43,0.64},1" "$file" ;;
    *)      echo "usage: $0 [gui|full|window|area]" >&2; exit 2 ;;
esac || exit 1

xclip -selection clipboard -t image/png -i "$file"
shutter=/usr/share/sounds/freedesktop/stereo/camera-shutter.oga
[ -r "$shutter" ] && command -v pw-play >/dev/null && pw-play --volume 0.4 "$shutter" 2>/dev/null &
notify-send -a screenshot -i "$file" "󰄀  Screenshot" "$(basename "$file") · copied to clipboard"
