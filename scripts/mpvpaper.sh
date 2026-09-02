#!/usr/bin/env bash

# Diretório onde os wallpapers estão armazenados
WALLPAPER_DIR="$HOME/.config/mpvpaper/"

# Se nenhum arquivo for passado como argumento, pega um arquivo aleatório da pasta
if [ -z "$1" ]; then
  WALLPAPER=$(find "$WALLPAPER_DIR" -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.webm" -o -name "*.png" -o -name "*.jpg" -o -name "*.gif" \) | shuf -n 1)
else
  WALLPAPER="$1"
fi

if [ -z "$WALLPAPER" ]; then
  echo "Nenhum papel de parede encontrado em $WALLPAPER_DIR"
  exit 1
fi

# Encerra qualquer instância anterior do mpvpaper para não acumular processos
killall -9 mpvpaper 2>/dev/null

# Opções para garantir performance e ausência de áudio
MPV_OPTS="no-audio loop hwdec=auto"

echo "Aplicando papel de parede: $WALLPAPER"
mpvpaper -o "$MPV_OPTS" '*' "$WALLPAPER" &
