#!/bin/sh
# Toggle a drop-down terminal that lives in the scratchpad; spawn it on first use.
# The for_window rule in the i3 config floats/sizes/hides it when it first appears.
cls=dropdown-term

if i3-msg -t get_tree | jq -e --arg c "$cls" '.. | objects | select(.window_properties?.class? == $c)' >/dev/null 2>&1; then
    exec i3-msg "[class=\"$cls\"] scratchpad show" >/dev/null
fi
exec kitty --class "$cls"
