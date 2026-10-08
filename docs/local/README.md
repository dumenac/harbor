# ~/.config/i3/local — yours

Harbor's installer never touches this folder, so everything personal lives here and survives
updates (`git pull && ./install.sh`).

| File | What it does |
| --- | --- |
| `tokens.toml` | Overrides for `~/.config/i3/harbor/tokens.toml`. Same layout; only the keys you set change. Run `~/.config/i3/scripts/harbor apply` afterwards. |
| `*.conf` | Extra i3 config, included at the end of Harbor's: workspace → monitor pins, `assign` rules, your own apps and keys. (i3 refuses a key that's already bound, so pick free combinations — `$mod+F1` lists them all.) |
| `monitors.sh` | Executable? Then it runs first at every i3 start/restart to set up your outputs with `xrandr`. See `extras/monitors.example.sh` in the repo. |
| `autostart.sh` | Executable? Then it runs last at every i3 start/restart. |
