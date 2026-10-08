#!/bin/sh
# volume.sh up|down|mute|mic — WirePlumber control with a HUD-style dunst progress card
sink=@DEFAULT_AUDIO_SINK@
src=@DEFAULT_AUDIO_SOURCE@

case "${1:-}" in
    up)   wpctl set-volume -l 1.0 "$sink" 5%+ ;;
    down) wpctl set-volume "$sink" 5%- ;;
    mute) wpctl set-mute "$sink" toggle ;;
    mic)
        wpctl set-mute "$src" toggle
        if wpctl get-volume "$src" | grep -q MUTED; then
            notify-send -a volume -h string:x-dunst-stack-tag:mic "󰍭  Microphone off"
        else
            notify-send -a volume -h string:x-dunst-stack-tag:mic "󰍬  Microphone on"
        fi
        exit 0
        ;;
    *) echo "usage: $0 up|down|mute|mic" >&2; exit 2 ;;
esac

raw=$(wpctl get-volume "$sink")                       # e.g. "Volume: 0.45 [MUTED]"
pct=$(printf '%s' "$raw" | awk '{printf "%d", $2 * 100 + 0.5}')
case "$raw" in
    *MUTED*) notify-send -a volume -h string:x-dunst-stack-tag:volume -h int:value:0 "󰝟  Muted" ;;
    *)
        if   [ "$pct" -lt 34 ]; then icon="󰕿"
        elif [ "$pct" -lt 67 ]; then icon="󰖀"
        else                         icon="󰕾"; fi
        notify-send -a volume -h string:x-dunst-stack-tag:volume -h int:value:"$pct" "$icon  Volume  $pct%"
        ;;
esac
pkill -USR1 -x harbor-bar 2>/dev/null
exit 0
