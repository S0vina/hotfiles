#!/usr/bin/env bash

set -e

echo "==> Instalando dependências essenciais para o Niri..."
# Adicione os pacotes que compõem o seu ecossistema no Niri
DEPS=(
  niri
  xwayland-satellite # Suporte a apps X11 no Niri
  waybar             # Barra de status
  fuzzel             # App launcher leve em Wayland
  mako               # Daemon de notificações
  swaybg             # Gerenciador de wallpaper
  foot               # Emulador de terminal
)

sudo pacman -S --needed --noconfirm "${DEPS[@]}"

echo "==> Aplicando links simbólicos dos dotfiles..."
stow -t "$HOME" config

echo "==> Instalação e configuração concluídas com sucesso!"
