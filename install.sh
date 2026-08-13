#!/usr/bin/env sh
set -eu

SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR="$HOME/.local/lib/hyde-display-settings"
STAGE_DIR="$HOME/.local/lib/.hyde-display-settings-stage-$$"
OLD_DIR="$HOME/.local/lib/.hyde-display-settings-old-$$"
INSTALL_COMPLETE=0
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
SERVICE_DIR="$HOME/.config/systemd/user"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/hyde-display-settings"

cleanup() {
    status=$?
    rm -rf "$STAGE_DIR"
    if [ "$INSTALL_COMPLETE" -eq 0 ] && [ -d "$OLD_DIR" ]; then
        rm -rf "$APP_DIR"
        mv "$OLD_DIR" "$APP_DIR"
    else
        rm -rf "$OLD_DIR"
    fi
    return "$status"
}
trap cleanup EXIT HUP INT TERM

for command in python systemctl hyprctl hypridle hyprsunset brightnessctl waybar pkill pgrep; do
    command -v "$command" >/dev/null 2>&1 || { printf '%s\n' "Missing required command: $command" >&2; exit 1; }
done
python -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' || { printf '%s\n' "Python 3.11 or newer is required" >&2; exit 1; }
python -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")' || {
    printf '%s\n' "Missing GTK 4/libadwaita Python bindings (python-gobject, gtk4, libadwaita)" >&2
    exit 1
}
python -m compileall -q "$SOURCE_DIR/src"
python "$SOURCE_DIR/src/waybar_integration.py" check --module "$SOURCE_DIR/waybar/custom-display-settings.jsonc"

mkdir -p "$STAGE_DIR/src" "$BIN_DIR" "$DESKTOP_DIR" "$SERVICE_DIR"
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
cp "$SOURCE_DIR/hyde-display-settings" "$SOURCE_DIR/hyde-screen-time-tracker" "$SOURCE_DIR/hyde-display-settings-waybar" "$STAGE_DIR/"
cp "$SOURCE_DIR/src/"*.py "$STAGE_DIR/src/"
chmod +x "$STAGE_DIR/hyde-display-settings" "$STAGE_DIR/hyde-screen-time-tracker" "$STAGE_DIR/hyde-display-settings-waybar"
if [ -d "$APP_DIR" ]; then
    mv "$APP_DIR" "$OLD_DIR"
fi
mv "$STAGE_DIR" "$APP_DIR"
cp "$SOURCE_DIR/io.github.hyde.DisplaySettings.desktop" "$DESKTOP_DIR/"
cp "$SOURCE_DIR/io.github.hyde.ScreenTimeTracker.service" "$SERVICE_DIR/"
ln -sfn "$APP_DIR/hyde-display-settings" "$BIN_DIR/hyde-display-settings"
ln -sfn "$APP_DIR/hyde-display-settings-waybar" "$BIN_DIR/hyde-display-settings-waybar"
python "$APP_DIR/src/waybar_integration.py" install --module "$SOURCE_DIR/waybar/custom-display-settings.jsonc"
systemctl --user daemon-reload
systemctl --user enable io.github.hyde.ScreenTimeTracker.service
systemctl --user restart io.github.hyde.ScreenTimeTracker.service
if ! command -v nwg-displays >/dev/null 2>&1; then
    printf '%s\n' "Optional: install nwg-displays for visual monitor arrangement."
fi
INSTALL_COMPLETE=1
printf '%s\n' "Installed. Display Settings is available from the application menu and Waybar."
