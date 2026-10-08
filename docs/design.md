# Harbor — the design system

Harbor is an i3 desktop that behaves like one product. Every surface — window borders, the
bar, the launcher, notifications, the terminal, GTK apps, the lock screen, even `fastfetch` —
is rendered from one file of design tokens, so it changes together. Twice a day it changes
on its own: at 20:00 the lighthouse on the wallpaper switches on and the whole desktop follows.

## Principles

1. **Quiet by default.** The bar shows four things: now playing, Wi-Fi, volume, the time. CPU,
   temperature, memory and disk appear only when something needs attention, then go away.
2. **One accent, and it means focus.** The focused window, the active tab, the selected row,
   the typing ring on the lock screen: all accent. Nothing else is coloured.
3. **Day and night are one design, not two themes.** Same layout, same type, same spacing;
   only the light changes — harbor blue on paper white by day, lantern amber on slate at night.
4. **Glass, not chrome.** Panels are translucent and blurred over the wallpaper; the bar mixes
   the wallpaper's sky into its colour so it reads as frosted glass even without a compositor.
5. **Motion explains, never performs.** One ease-out curve, 120–260 ms. New windows rise out of
   the desk, notifications slide in from the edge, workspaces cross-dissolve, the drop-down
   terminal drops down. The only slow thing is dusk: a 1.4 s crossfade at 20:00.
6. **Everything has a keyboard path and a mouse path.** Click the clock for a calendar, the
   sliders icon for the Control Center, scroll the volume; or `$mod+c`, `$mod+d`, `$mod+F1`.

## Tokens

All in [`config/i3/harbor/tokens.toml`](../config/i3/harbor/tokens.toml). Override any of them in
`~/.config/i3/local/tokens.toml`; `harbor apply` re-renders everything.

### Colour

| Token | Day | Night | Used for |
| --- | --- | --- | --- |
| `canvas` | ![](https://img.shields.io/badge/-%23fbfbf9-fbfbf9?style=flat-square) `#fbfbf9` | ![](https://img.shields.io/badge/-%2314181d-14181d?style=flat-square) `#14181d` | launcher, notifications, Control Center |
| `raised` | ![](https://img.shields.io/badge/-%23f1f1ee-f1f1ee?style=flat-square) `#f1f1ee` | ![](https://img.shields.io/badge/-%231d232a-1d232a?style=flat-square) `#1d232a` | inactive tabs, fields |
| `hairline` | ![](https://img.shields.io/badge/-%23e2e2de-e2e2de?style=flat-square) `#e2e2de` | ![](https://img.shields.io/badge/-%232a3038-2a3038?style=flat-square) `#2a3038` | 1 px dividers and frames |
| `text` | ![](https://img.shields.io/badge/-%2315171a-15171a?style=flat-square) `#15171a` | ![](https://img.shields.io/badge/-%23ecedee-ecedee?style=flat-square) `#ecedee` | primary text |
| `text_muted` | ![](https://img.shields.io/badge/-%235b6068-5b6068?style=flat-square) `#5b6068` | ![](https://img.shields.io/badge/-%239da3ab-9da3ab?style=flat-square) `#9da3ab` | secondary text, dates |
| `text_faint` | ![](https://img.shields.io/badge/-%238a8f96-8a8f96?style=flat-square) `#8a8f96` | ![](https://img.shields.io/badge/-%236b727b-6b727b?style=flat-square) `#6b727b` | hints, placeholders |
| `accent` | ![](https://img.shields.io/badge/-%232e6da4-2e6da4?style=flat-square) `#2e6da4` harbor blue | ![](https://img.shields.io/badge/-%23e8a94a-e8a94a?style=flat-square) `#e8a94a` lantern amber | focus, selection, progress |
| `danger` | ![](https://img.shields.io/badge/-%23d0392e-d0392e?style=flat-square) `#d0392e` | ![](https://img.shields.io/badge/-%23ff6b5e-ff6b5e?style=flat-square) `#ff6b5e` | urgent, wrong password |

Derived at render time:

- **`bar`** = `base` mixed with the average colour of the wallpaper's top strip (`vibrancy`:
  0.30 by day, 0.55 at night) — the bar looks like frosted glass over *your* sky.
- **pills** (focused / visible workspace) = `bar` mixed 12 % / 6 % toward `text`.
- **terminal** colours are their own set (`[terminal]`): kitty stays dark in both appearances so
  TUIs keep working; the background shifts from dusk blue to harbor night and the cursor takes
  the accent.

### Type

| Token | Value | Where |
| --- | --- | --- |
| `ui` | Inter | everything with words |
| `display` | Inter Display (Light) | the lock-screen clock |
| `mono` | JetBrains Mono | terminal, calendar, shortcut sheet |
| `icons` | JetBrainsMono Nerd Font | Material Design glyphs, used like SF Symbols — one weight, a step larger than the text beside them |

Sizes are **pixels**, like CSS (`size_bar = 14`, `size_menu = 15`, …). i3 and i3bar scale
fonts by the X screen's DPI while rofi and dunst use 96, so point sizes would come out
different everywhere; Pango's `14px` comes out the same.

### Shape

`radius_window 12` · `radius_panel 16` · `radius_notify 14` · `radius_small 8` ·
`border 2` · `gap_inner 10` · `gap_outer 3`. Notification cards sit **on the window grid** —
their right and top edges line up with the tiled windows (`notify_offset = "auto"` measures it).

### Motion

One curve — `cubic-bezier(0.2, 0.8, 0.2, 1)` — at three speeds: 120 ms (dismiss, hide),
180 ms (open, show), 260 ms (slide). The Day ⇄ Night crossfade is 1.4 s, with the chrome
switching at its midpoint.

## How it renders

```mermaid
flowchart LR
    T[tokens.toml] --> H{{harbor}}
    L[local/tokens.toml] --> H
    W[day / night wallpaper] --> H
    H --> I3[i3 colours + bar<br/>look.conf → generated.conf]
    H --> R[rofi harbor.rasi]
    H --> D[dunst 90-harbor.conf]
    H --> K[kitty harbor.conf]
    H --> G[GTK · Firefox<br/>xsettingsd, settings.ini, gsettings]
    H --> F[fastfetch config + logo]
    H --> P[wallpaper composite<br/>+ crossfade frames]
    H --> LK[lock screen background]
    WT[harbor watch] -- "20:00 / 07:00, Focus timer" --> H
```

`harbor watch` is a tiny per-session daemon: it sleeps until the next switch or Focus deadline,
then runs `harbor apply --fade`. Everything is cached — composites per monitor layout, the
14-frame crossfade, the lock background, the fastfetch logo — so the switch costs nothing.
