# Troubleshooting

**`harbor check` is the first thing to run.** It renders both appearances and validates them,
including the i3 config, and says what's wrong.

### Text in the bar/titles is a different size than in the launcher
i3 and i3bar size fonts by the X screen's DPI (or `Xft.dpi`), rofi and dunst by 96. Harbor
gives every size in `px` so they match. If something is still off, check you haven't set a
font in points in `local/i3.conf`.

### Gaps, borders and the bar look bigger than the numbers in tokens.toml
Expected on HiDPI: i3 treats them as logical pixels and scales them by DPI ÷ 96. Notification
cards follow (`notify_offset = "auto"` measures the real bar and gaps).

### New windows or notifications don't appear (picom)
If picom was killed and restarted inside a running session, it can lose track of windows.
Reload it instead of restarting: `pkill -USR1 picom`. If it's already stuck, log out and in.

### No blur / shadows / animations
Needs picom **12** with the GLX backend. Under xrdp/VNC there's no GPU, so autostart skips
picom on purpose: everything still works, just flat. On NVIDIA keep `use-damage = false`.

### The launcher has no Calc tab
Install `rofi-calc` (Arch) or run `extras/build-rofi-calc.sh`. The tab appears automatically.

### The lock screen has no clock
That's plain i3lock. Install `i3lock-color` (Arch) or run `extras/build-i3lock-color.sh`.

### GTK apps / Firefox don't switch at night
Needs `xsettingsd` (started by autostart). Firefox must be on its default *System theme — auto*.

### The Bluetooth tray icon is dark on the dark bar
Harbor restarts `blueman-applet` at the switch because its tray icon never re-reads the icon
theme. Other tray apps that don't follow GTK themes may need the same.

### Icons show as boxes
Install the JetBrainsMono Nerd Font: `extras/install-fonts.sh`.

### Everything is wrong and I want my old desktop back
`./uninstall.sh` removes Harbor and restores the backup the installer made.
