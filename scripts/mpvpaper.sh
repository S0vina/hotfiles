#!/usr/bin/env bash

# Wallpaper directory
WALLPAPER_DIR="$HOME/.config/mpvpaper/"

# select a random photo
if [ -z "$1" ]; then
  WALLPAPER=$(find "$WALLPAPER_DIR" -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.webm" -o -name "*.png" -o -name "*.jpg" -o -name "*.gif" \) | shuf -n 1)
else
  WALLPAPER="$1"
fi

# no wallpaper founded
if [ -z "$WALLPAPER" ]; then
  echo "Nenhum papel de parede encontrado em $WALLPAPER_DIR"
  exit 1
fi

# kills any wallpaper process created before
killall -9 mpvpaper 2>/dev/null

# options for resize, loop and no audio for videos wallpapers
MPV_OPTS="no-audio loop hwdec=auto panscan=1.0"

# Calls mpv command and set the wallpaper
mpvpaper -o "$MPV_OPTS" '*' "$WALLPAPER" &
