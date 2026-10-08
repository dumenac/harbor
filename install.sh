#!/usr/bin/env bash
# ╭──────────────────────────────────────────────────────────────────────────────╮
# │  Harbor installer                                                             │
# │                                                                               │
# │  ./install.sh            check dependencies, back up, copy Harbor into ~/.config│
# │  ./install.sh --link     symlink instead of copy (edit the repo, see it live)  │
# │  ./install.sh --check    only report dependencies                             │
# │  ./install.sh --yes      don't ask                                            │
# │                                                                               │
# │  Everything it replaces is moved to ~/.local/share/harbor/backups/<time>/,    │
# │  and ./uninstall.sh puts it back. ~/.config/i3/local/ is yours: never touched.│
# ╰──────────────────────────────────────────────────────────────────────────────╯
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/harbor"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$DATA/backups/$STAMP"
MANIFEST="$DATA/manifest"

MODE=copy ASSUME_YES=0 CHECK_ONLY=0 FORCE=0
for arg in "$@"; do
    case "$arg" in
        --link)  MODE="link" ;;
        --yes|-y) ASSUME_YES=1 ;;
        --check) CHECK_ONLY=1 ;;
        --force) FORCE=1 ;;
        -h|--help) sed -n '2,13p' "$0" | sed 's/^# \?//'; exit 0 ;;
        *) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

if [ -t 1 ]; then
    B=$'\e[1m' D=$'\e[2m' R=$'\e[0m' OK=$'\e[38;2;140;201;143m' NO=$'\e[38;2;240;113;106m'
    MAYBE=$'\e[38;2;232;178;90m' ACC=$'\e[38;2;110;168;220m'
else
    B='' D='' R='' OK='' NO='' MAYBE='' ACC=''
fi
say()  { printf '%s\n' "$*"; }
section() { printf '\n%s%s%s\n' "$B" "$*" "$R"; }

cat <<EOF

  ${ACC}󰧿${R}  ${B}Harbor${R} ${D}— a calm i3 rice that follows the light${R}

EOF

# ── 1. dependencies ──────────────────────────────────────────────────────────────
# shellcheck source=/dev/null
. /etc/os-release 2>/dev/null || true
case " ${ID:-} ${ID_LIKE:-} " in
    *" arch "*)                PM=arch ;;
    *" debian "*|*" ubuntu "*) PM=debian ;;
    *" fedora "*|*" rhel "*)   PM=fedora ;;
    *)                         PM=other ;;
esac
# name @ test @ debian package @ arch package @ fedora package @ what it's for
REQUIRED=(
    "i3@command -v i3@i3-wm@i3-wm@i3@the window manager (4.22+)"
    "python 3.11+@python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'@python3@python@python3@harbor, the bar, menus"
    "rofi@command -v rofi@rofi@rofi@rofi@launcher, Control Center, menus"
    "dunst@command -v dunst@dunst@dunst@dunst@notifications"
    "feh@command -v feh@feh@feh@feh@sets the wallpaper"
    "ImageMagick@command -v magick || command -v convert@imagemagick@imagemagick@ImageMagick@wallpaper, lock screen, logo"
    "xrandr@command -v xrandr@x11-xserver-utils@xorg-xrandr@xrandr@monitor layout"
    "xprop/xset@command -v xprop && command -v xset@x11-utils@xorg-xprop@xprop@session markers, Keep Awake"
    "jq@command -v jq@jq@jq@jq@drop-down terminal"
    "xclip@command -v xclip@xclip@xclip@xclip@clipboard, calculator, screenshots"
    "fontconfig@command -v fc-match@fontconfig@fontconfig@fontconfig@finding fonts"
    "notify-send@command -v notify-send@libnotify-bin@libnotify@libnotify@notifications from scripts"
)
RECOMMENDED=(
    "picom 12@picom --version 2>/dev/null | grep -Eq 'v1[2-9]'@picom@picom@picom@blur, shadows, corners, motion"
    "kitty@command -v kitty@kitty@kitty@kitty@the Harbor terminal"
    "python3-xlib@python3 -c 'import Xlib'@python3-xlib@python-xlib@python3-xlib@clipboard history"
    "xsettingsd@command -v xsettingsd@xsettingsd@xsettingsd@xsettingsd@GTK apps & Firefox follow Day/Night"
    "i3lock-color@[ -x \"\$HOME/.local/opt/i3lock-color/bin/i3lock-color\" ] || command -v i3lock-color || i3lock --version 2>&1 | grep -q '\\.c\\.'@— extras/build-i3lock-color.sh@i3lock-color@— extras/build-i3lock-color.sh@lock screen clock & ring"
    "i3lock@command -v i3lock@i3lock@i3lock@i3lock@lock screen fallback + PAM file"
    "xss-lock@command -v xss-lock@xss-lock@xss-lock@xss-lock@lock on suspend / idle"
    "rofi-calc@[ -e \"\$HOME/.local/lib/rofi/calc.so\" ] || ls /usr/lib/rofi/calc.so /usr/lib/*/rofi/calc.so >/dev/null 2>&1@— extras/build-rofi-calc.sh@rofi-calc@— extras/build-rofi-calc.sh@Calc tab in the launcher"
    "qalc@command -v qalc@qalc@libqalculate@qalculate@calculator engine"
    "emoji list@[ -e /usr/share/unicode/emoji/emoji-test.txt ] || [ -e /usr/share/unicode-emoji/emoji-test.txt ]@unicode-data@unicode-emoji@unicode-emoji@Emoji tab"
    "xdotool@command -v xdotool@xdotool@xdotool@xdotool@emoji typing, window screenshots"
    "maim@command -v maim@maim@maim@maim@screenshots"
    "flameshot@command -v flameshot@flameshot@flameshot@flameshot@annotated screenshots"
    "playerctl@command -v playerctl@playerctl@playerctl@playerctl@now playing in the bar"
    "PipeWire tools@command -v wpctl && command -v pactl@wireplumber pulseaudio-utils@wireplumber libpulse@wireplumber pulseaudio-utils@volume in the bar"
    "fastfetch@command -v fastfetch@fastfetch@fastfetch@fastfetch@the About card"
    "gammastep@command -v gammastep@gammastep@gammastep@gammastep@Night Shift"
    "dex@command -v dex@dex@dex@dex-autostart@XDG autostart entries"
    "Papirus icons@[ -d /usr/share/icons/Papirus ] || [ -d \"\$HOME/.local/share/icons/Papirus\" ]@papirus-icon-theme@papirus-icon-theme@papirus-icon-theme@app & tray icons"
    "Breeze cursor@[ -d /usr/share/icons/breeze_cursors ]@breeze-cursor-theme@breeze@breeze-cursor-theme@cursor"
    "Inter font@fc-list : family | grep -qx 'Inter'@fonts-inter@inter-font@rsms-inter-fonts@UI type — or extras/install-fonts.sh"
    "JetBrains Mono@fc-list : family | grep -q 'JetBrains Mono'@fonts-jetbrains-mono@ttf-jetbrains-mono@jetbrains-mono-fonts@terminal type — or extras/install-fonts.sh"
    "Nerd Font glyphs@fc-list : family | grep -q 'JetBrainsMono Nerd Font'@— extras/install-fonts.sh@ttf-jetbrains-mono-nerd@— extras/install-fonts.sh@icons everywhere"
)
missing_req=() missing_pkgs=()
report() {
    local level=$1 entry name test deb arch fed why pkg
    shift
    for entry in "$@"; do
        IFS='@' read -r name test deb arch fed why <<<"$entry"
        if bash -c "$test" >/dev/null 2>&1; then
            printf '  %s✓%s %-17s %s%s%s\n' "$OK" "$R" "$name" "$D" "$why" "$R"
        else
            if [ "$level" = required ]; then
                printf '  %s✗%s %-17s %s\n' "$NO" "$R" "$name" "$why"
                missing_req+=("$name")
            else
                printf '  %s·%s %-17s %s%s (optional)%s\n' "$MAYBE" "$R" "$name" "$D" "$why" "$R"
            fi
            case $PM in debian) pkg=$deb ;; arch) pkg=$arch ;; fedora) pkg=$fed ;; *) pkg= ;; esac
            if [ -n "$pkg" ] && [ "${pkg#—}" = "$pkg" ]; then   # "— script" = not packaged
                missing_pkgs+=("$pkg")
            fi
        fi
    done
    return 0
}
section "Required"
report required "${REQUIRED[@]}"
section "Recommended"
report recommended "${RECOMMENDED[@]}"

if [ ${#missing_pkgs[@]} -gt 0 ]; then
    section "To install what's missing"
    case $PM in
        debian) say "  sudo apt install ${missing_pkgs[*]}" ;;
        arch)   say "  sudo pacman -S --needed ${missing_pkgs[*]}" ;;
        fedora) say "  sudo dnf install ${missing_pkgs[*]}" ;;
    esac
    say "  ${D}Not packaged everywhere: extras/build-i3lock-color.sh, extras/build-rofi-calc.sh, extras/install-fonts.sh${R}"
fi
[ "$CHECK_ONLY" = 1 ] && exit 0
if [ ${#missing_req[@]} -gt 0 ] && [ "$FORCE" = 0 ]; then
    say ""
    say "${NO}✗${R} Missing required: ${missing_req[*]}. Install them and run again (or --force)."
    exit 1
fi

# ── 2. plan ──────────────────────────────────────────────────────────────────────
# repo path → installed path. Config mirrors ~/.config; wallpapers go to ~/.local/share/harbor.
declare -a SRC DST
while IFS= read -r -d '' f; do
    rel=${f#"$REPO/config/"}
    SRC+=("$f"); DST+=("$CONF/$rel")
done < <(find "$REPO/config" -type f -print0 | sort -z)
while IFS= read -r -d '' f; do
    rel=${f#"$REPO/wallpapers/"}
    SRC+=("$f"); DST+=("$DATA/wallpapers/$rel")
done < <(find "$REPO/wallpapers" -type f \( -name '*.jpg' -o -name '*.png' \) -print0 2>/dev/null | sort -z)
# files harbor generates over whatever you had there
GENERATED=(
    "$CONF/gtk-3.0/settings.ini" "$CONF/gtk-4.0/settings.ini" "$CONF/xsettingsd/xsettingsd.conf"
    "$CONF/fastfetch/config.jsonc" "$CONF/kitty/harbor.conf" "$CONF/rofi/harbor.rasi"
    "$CONF/dunst/dunstrc.d/90-harbor.conf" "$CONF/i3/harbor/generated.conf"
)

section "Plan"
say "  ${#SRC[@]} files → ~/.config and ~/.local/share/harbor (${B}$MODE${R})"
say "  replaced files are moved to ${D}${BACKUP/#$HOME/\~}${R}"
say "  your additions go in ${D}~/.config/i3/local/${R} (created if missing, never overwritten)"
if [ "$ASSUME_YES" = 0 ]; then
    printf '\n  Continue? [y/N] '
    read -r answer
    case "$answer" in y|Y|yes) ;; *) say "  Nothing changed."; exit 0 ;; esac
fi

# ── 3. back up, then install ─────────────────────────────────────────────────────
backed=0
backup() {   # move $1 into the backup tree, keeping its path relative to $HOME
    local f=$1 rel
    rel=${f#"$HOME/"}
    mkdir -p "$BACKUP/$(dirname "$rel")"
    mv -- "$f" "$BACKUP/$rel"
    backed=$((backed + 1))
}
mkdir -p "$DATA"
: > "$MANIFEST.new"
for i in "${!SRC[@]}"; do
    src=${SRC[$i]} dst=${DST[$i]}
    if [ -L "$dst" ] && [ "$(readlink -- "$dst")" = "$src" ]; then
        :                                           # already linked to this repo
    elif [ -e "$dst" ] || [ -L "$dst" ]; then
        if [ "$MODE" = copy ] && [ ! -L "$dst" ] && cmp -s -- "$src" "$dst"; then
            :                                       # identical copy: keep it
        else
            backup "$dst"
        fi
    fi
    mkdir -p -- "$(dirname "$dst")"
    if [ "$MODE" = link ]; then
        [ -L "$dst" ] || ln -s -- "$src" "$dst"
    elif [ ! -e "$dst" ]; then
        install -m "$( [ -x "$src" ] && echo 755 || echo 644 )" -- "$src" "$dst"
    fi
    printf '%s\n' "$dst" >> "$MANIFEST.new"
done
for g in "${GENERATED[@]}"; do
    if [ -e "$g" ] && ! grep -q "generated by harbor" "$g" 2>/dev/null; then
        backup "$g"
    fi
    printf 'generated:%s\n' "$g" >> "$MANIFEST.new"
done
{ printf 'mode:%s\nbackup:%s\nrepo:%s\n' "$MODE" "$BACKUP" "$REPO"; cat "$MANIFEST.new"; } > "$MANIFEST"
rm -f "$MANIFEST.new"
chmod +x "$CONF/i3/scripts/"* 2>/dev/null || true

# ── 4. your corner: ~/.config/i3/local ───────────────────────────────────────────
LOCAL="$CONF/i3/local"
if [ ! -d "$LOCAL" ]; then
    mkdir -p "$LOCAL"
    cp "$REPO/docs/local/README.md" "$LOCAL/README.md"
    cp "$REPO/docs/local/i3.conf" "$LOCAL/i3.conf"
    cp "$REPO/docs/local/tokens.toml" "$LOCAL/tokens.toml"
    say "  created ~/.config/i3/local/ (README, i3.conf, tokens.toml — all commented out)"
fi

# ── 5. render ────────────────────────────────────────────────────────────────────
section "Rendering"
if "$CONF/i3/scripts/harbor" render; then
    say "  ${OK}✓${R} generated i3, rofi, dunst, kitty, GTK and fastfetch config"
else
    say "  ${NO}✗${R} harbor render failed — run ~/.config/i3/scripts/harbor check for details"
fi
if [ -n "${DISPLAY:-}" ] && i3-msg -t get_version >/dev/null 2>&1; then
    say "  You're in i3: press ${B}\$mod+Shift+r${R} to restart into Harbor (your windows stay)."
else
    say "  Log into i3 and Harbor starts by itself."
fi

section "Done"
say "  ${OK}✓${R} Harbor installed ($MODE). $backed file(s) backed up to ${BACKUP/#$HOME/\~}"
say "  Start here: ${B}\$mod+c${R} Control Center · ${B}\$mod+d${R} launcher · ${B}\$mod+F1${R} every shortcut"
say "  Make it yours: ~/.config/i3/local/tokens.toml, then  ~/.config/i3/scripts/harbor apply"
say "  Undo: ./uninstall.sh"
say ""
