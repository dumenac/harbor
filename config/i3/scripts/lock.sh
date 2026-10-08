#!/bin/sh
# Lock screen: the Edgartown wallpaper of the current appearance, blurred, with today's date
# and a lighthouse (lit at night) — rendered by harbor, cached once per day.
# Runs i3lock in the foreground (-n): xss-lock needs the locker to stay alive until unlocked.
# harbor falls back to a plain-colour i3lock if anything about the image fails.
exec "$HOME/.config/i3/scripts/harbor" lock
