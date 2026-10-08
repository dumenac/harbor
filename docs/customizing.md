# Make it yours

Everything personal goes in **`~/.config/i3/local/`** — the installer never touches it, so you
can `git pull && ./install.sh` any time.

## Colours, schedule, sounds — `local/tokens.toml`

Same layout as [`tokens.toml`](../config/i3/harbor/tokens.toml); only the keys you set change.

```toml
[schedule]
night_starts = "21:30"
day_starts   = "06:30"

[day]
accent = "#7c3aed"        # violet by day…
[night]
accent = "#f59e0b"        # …amber at night

[sound]
transition = ""           # no chime at the switch
```

Then `~/.config/i3/scripts/harbor apply`. Bar font or size changes need an i3 restart
(`$mod+Shift+r`), everything else switches live.

## Your own wallpapers

Any pair of images works — each monitor gets a "cover" fit, and the bar picks up the colour of
your sky automatically.

```toml
[day]
wallpaper = "~/Pictures/coast-day.jpg"
[night]
wallpaper = "~/Pictures/coast-night.jpg"

[fastfetch]
logo_crop = [0.30, 0.20, 0.30, 0.55]   # x, y, width, height (fractions) of the part shown in the card
```

No night version? Make one: `magick day.jpg -modulate 55,70 -fill '#0d1726' -colorize 35% night.jpg`.

## Monitors — `local/monitors.sh`

Copy [`extras/monitors.example.sh`](../extras/monitors.example.sh) to
`~/.config/i3/local/monitors.sh`, make it executable and set your outputs. It runs first on every
i3 start and restart, before the wallpaper is composed for the layout. Pin workspaces in
`local/i3.conf`:

```
workspace $ws1 output DP-0
workspace $ws6 output HDMI-0 DP-0
```

## Your apps and keys — `local/*.conf`

Included at the end of Harbor's i3 config, so `$mod`, `$term`, `$ws1`… all work.

```
bindsym $mod+Shift+g exec gimp
assign [class="(?i)firefox"] $ws2
for_window [class="Spotify"] move to workspace $ws9
```

i3 refuses a key that's already bound — `$mod+F1` lists every binding, so pick a free one (or
change Harbor's in `config/i3/config` if you use `--link`).

## Your own startup — `local/autostart.sh`

Executable? It runs at the end of every i3 start/restart, after Harbor's daemons are up.

## The look itself

- `config/i3/harbor/look.conf` — i3's colours, fonts, gaps and the bar block (template).
- `config/rofi/config.rasi` — launcher layout. Colours come from the generated `harbor.rasi`.
- `config/dunst/dunstrc` — notification layout and per-app rules.
- `config/picom/picom.conf` — corners, shadows, blur, and every animation.
- `config/i3/harbor/fastfetch.jsonc` — the About card (template).

Installed with `--link`, those are symlinks into your clone — edit, `harbor apply`, commit.
