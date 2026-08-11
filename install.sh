#!/usr/bin/env sh
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR="$HOME/.local/lib/hyde-display-settings"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
SERVICE_DIR="$HOME/.config/systemd/user"

mkdir -p "$APP_DIR/src" "$BIN_DIR" "$DESKTOP_DIR" "$SERVICE_DIR"
cp "$SOURCE_DIR/hyde-display-settings" "$SOURCE_DIR/hyde-screen-time-tracker" "$APP_DIR/"
cp "$SOURCE_DIR/src/"*.py "$APP_DIR/src/"
cp "$SOURCE_DIR/io.github.hyde.DisplaySettings.desktop" "$DESKTOP_DIR/"
cp "$SOURCE_DIR/io.github.hyde.ScreenTimeTracker.service" "$SERVICE_DIR/"
ln -sfn "$APP_DIR/hyde-display-settings" "$BIN_DIR/hyde-display-settings"
chmod +x "$APP_DIR/hyde-display-settings" "$APP_DIR/hyde-screen-time-tracker"
systemctl --user daemon-reload
systemctl --user enable --now io.github.hyde.ScreenTimeTracker.service
printf '%s\n' "Installed. Open Display Settings from the application menu."
