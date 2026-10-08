# Changelog

## 1.0.0 — 2026-10-08

First public release.

- **Design system**: one `tokens.toml` (colour, type in px, shape, motion, sound) rendered into i3,
  i3bar, rofi, dunst, kitty, GTK/Firefox (xsettingsd), fastfetch, the wallpaper and the lock screen.
- **Day ⇄ Night** at 20:00 / 07:00 with a 1.4 s crossfade; chrome switches at the midpoint; Auto,
  Light or Dark; flipping back to the clock returns to Auto.
- **Bar** (`bar.py`): quiet by default, stats only when something's wrong, click/scroll actions,
  Focus countdown.
- **Launcher**: Apps · Calc (rofi-calc) · Emoji · Clipboard (XFixes, RAM-only, skips secrets) · Windows.
- **Control Center**, power menu, calendar card, readable shortcut sheet (`$mod+F1`).
- **Focus** mode: Do Not Disturb, softened captioned wallpaper, countdown, chime.
- **Lock screen** (i3lock-color): live clock, lighthouse avatar, accent ring; plain i3lock fallback.
- **picom 12** motion: windows rise, notifications slide, workspaces cross-dissolve, drop-down slides.
- **Installer** with dependency report per distro, backups, `--link` mode, local overrides in
  `~/.config/i3/local/`, manifest-based `uninstall.sh`; `harbor check` + CI.
