#!/usr/bin/env sh
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR="$HOME/.local/lib/hyde-display-settings"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
SERVICE_DIR="$HOME/.config/systemd/user"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/hyde-display-settings"

for command in python systemctl; do
    command -v "$command" >/dev/null 2>&1 || { printf '%s\n' "Missing required command: $command" >&2; exit 1; }
done
python -m compileall -q "$SOURCE_DIR/src"
python "$SOURCE_DIR/src/waybar_integration.py" check --module "$SOURCE_DIR/waybar/custom-display-settings.jsonc"

mkdir -p "$APP_DIR/src" "$BIN_DIR" "$DESKTOP_DIR" "$SERVICE_DIR"
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
cp "$SOURCE_DIR/hyde-display-settings" "$SOURCE_DIR/hyde-screen-time-tracker" "$SOURCE_DIR/hyde-display-settings-waybar" "$APP_DIR/"
cp "$SOURCE_DIR/src/"*.py "$APP_DIR/src/"
cp "$SOURCE_DIR/io.github.hyde.DisplaySettings.desktop" "$DESKTOP_DIR/"
cp "$SOURCE_DIR/io.github.hyde.ScreenTimeTracker.service" "$SERVICE_DIR/"
ln -sfn "$APP_DIR/hyde-display-settings" "$BIN_DIR/hyde-display-settings"
ln -sfn "$APP_DIR/hyde-display-settings-waybar" "$BIN_DIR/hyde-display-settings-waybar"
chmod +x "$APP_DIR/hyde-display-settings" "$APP_DIR/hyde-screen-time-tracker" "$APP_DIR/hyde-display-settings-waybar"
python "$APP_DIR/src/waybar_integration.py" install --module "$SOURCE_DIR/waybar/custom-display-settings.jsonc"
systemctl --user daemon-reload
systemctl --user enable io.github.hyde.ScreenTimeTracker.service
systemctl --user restart io.github.hyde.ScreenTimeTracker.service
printf '%s\n' "Installed. Display Settings is available from the application menu and Waybar."
