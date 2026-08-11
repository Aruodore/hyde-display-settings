#!/usr/bin/env sh
set -eu

APP_DIR="$HOME/.local/lib/hyde-display-settings"

systemctl --user disable --now io.github.hyde.ScreenTimeTracker.service 2>/dev/null || true
if [ -f "$APP_DIR/src/waybar_integration.py" ]; then
    python "$APP_DIR/src/waybar_integration.py" uninstall
fi
rm -f "$HOME/.local/bin/hyde-display-settings" "$HOME/.local/bin/hyde-display-settings-waybar"
rm -f "$HOME/.local/share/applications/io.github.hyde.DisplaySettings.desktop"
rm -f "$HOME/.config/systemd/user/io.github.hyde.ScreenTimeTracker.service"
rm -f "$APP_DIR/src/"*.py "$APP_DIR/hyde-display-settings" "$APP_DIR/hyde-display-settings-waybar" "$APP_DIR/hyde-screen-time-tracker"
rmdir "$APP_DIR/src" "$APP_DIR" 2>/dev/null || true
systemctl --user daemon-reload
printf '%s\n' "Uninstalled. Settings and screen-time history were kept."
