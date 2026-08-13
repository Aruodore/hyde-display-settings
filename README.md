# HyDE Display Settings

A native control center for display, idle, night-light, and screen-time settings on [HyDE](https://github.com/HyDE-Project/HyDE) and Hyprland.

HyDE Display Settings brings the controls that are normally spread across Hyprland configuration files and command-line tools into one GTK 4 and libadwaita app. It also adds today's active screen time to Waybar.

> [!IMPORTANT]
> This is an independent community project. It is not an official HyDE component or endorsed by the HyDE Project.

The project is currently alpha software. Backups are created before managed configuration is changed, but reviewing those changes before relying on them is recommended.

Releases follow [Semantic Versioning](https://semver.org/). See the
[changelog](CHANGELOG.md) for upgrade notes and unreleased work.

## Features

- View connected displays and open `nwg-displays` for visual monitor arrangement
- Adjust brightness on devices exposed through `brightnessctl`
- Schedule warmer color temperature with `hyprsunset`
- Configure ordered dim, lock, display-off, and suspend actions
- Track active time by application, locally and only after opt-in
- Compare this week with the same elapsed days last week, including daily totals, averages, and top apps
- Show today's total active time in a clickable Waybar module
- Follow the active GTK and HyDE theme through libadwaita
- Preserve unrelated Hyprland configuration using marked managed blocks

## What it manages

| Control | Backend | Behavior |
| --- | --- | --- |
| Monitor layout | `nwg-displays` | Opens the visual layout editor |
| Brightness | `brightnessctl` | Applies changes immediately |
| Night light | `hyprsunset` | Writes a scheduled managed profile |
| Idle actions | `hypridle`, `hyprlock`, systemd | Writes ordered managed listeners |
| Screen time | Local Python service and SQLite | Records active seconds by date and app class |
| Waybar | HyDE user modules and layouts | Shows today's total and opens the app on click |

## Privacy and safety

Screen-time tracking is disabled by default. When enabled, the tracker stores only:

- the local calendar date
- the active application's Wayland class
- the number of active seconds

It does not store window titles, keyboard input, screenshots, file names, browsing history, or window content. The tracker service is denied network access by systemd and pauses while the session is locked, idle, or all displays are powered off.

State is stored in `~/.local/state/hyde-display-settings/` with owner-only permissions. The app can erase all recorded history from its Screen Time page.

Applying settings updates only blocks marked `BEGIN HYDE DISPLAY SETTINGS` and `END HYDE DISPLAY SETTINGS` in the Hyprland configuration. Existing files receive uniquely timestamped backup copies before each change; the ten newest backups per managed file are retained.

## Requirements

The supported environment is an Arch Linux installation running HyDE, Hyprland, Waybar, and a user systemd session. Python 3.11 or newer is required.

Install the runtime packages with:

```sh
sudo pacman -S --needed python python-gobject gtk4 libadwaita \
  hypridle hyprlock hyprsunset brightnessctl nwg-displays waybar
```

`nwg-displays` is optional if the visual monitor-layout editor is not needed. Brightness support depends on a device exposed through `brightnessctl`.

## Install

Clone the repository and run the user-local installer:

```sh
git clone https://github.com/Aruodore/hyde-display-settings.git
cd hyde-display-settings
./install.sh
```

The installer performs a user-local installation under `~/.local`, enables the screen-time service, installs the Waybar module, and reloads Waybar. Enabling the service does not enable tracking; tracking remains off until switched on in the app.

The installer expects an active HyDE Waybar configuration at `~/.config/waybar/config.jsonc`. It never edits HyDE-owned files under `~/.local/share/waybar`.

After installation, open **Display Settings** from the application launcher, click the new Waybar time item, or run:

```sh
hyde-display-settings
```

Use **Save & Apply** to save idle and night-light settings. Brightness changes are immediate. The monitor-layout row launches `nwg-displays`, which owns and applies monitor layout configuration.

## Files and configuration

| Path | Purpose |
| --- | --- |
| `~/.config/hyde-display-settings/settings.json` | App preferences and tracking opt-in |
| `~/.config/hypr/hypridle.conf` | Managed idle listeners |
| `~/.config/hypr/hyprsunset.conf` | Managed night-light schedule |
| `~/.config/waybar/modules/custom-display-settings.jsonc` | User Waybar module definition |
| `~/.config/waybar/layouts/display-settings.jsonc` | Persistent HyDE Waybar layout |
| `~/.local/state/hyde-display-settings/screen-time.sqlite3` | Private local usage history |
| `~/.local/state/hyde-display-settings/tracker-health.json` | Tracker status and last successful heartbeat |

## Update

Update the source checkout, then run the installer again:

```sh
git pull --ff-only
./install.sh
```

The installation is idempotent. Existing settings and screen-time history are retained.

## Uninstall

```sh
./uninstall.sh
```

Uninstalling removes the app, launcher, service, and Waybar integration. User settings, configuration backups, and screen-time history are intentionally preserved so they can be recovered or removed manually.

## Development

Run the app directly from a checkout:

```sh
./hyde-display-settings
```

Run the test and validation suite:

```sh
python -W error -m unittest discover -v
python -m compileall -q src tests
bash -n install.sh uninstall.sh hyde-display-settings \
  hyde-display-settings-waybar hyde-screen-time-tracker
desktop-file-validate io.github.hyde.DisplaySettings.desktop
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

The tests use temporary directories and mocks. They do not overwrite the user's live Hyprland or Waybar configuration. GitHub Actions runs compilation, desktop-entry validation, shell checks, and unit tests on pushes and pull requests.

The application is intentionally small:

```text
src/app.py                 GTK and libadwaita interface
src/settings.py            configuration parsing, backups, and apply logic
src/tracker.py             local active-time collector
src/waybar.py              Waybar JSON output
src/waybar_integration.py  HyDE user-layout integration
tests/                     unit and installer integration tests
```

## Contributing

Bug reports, compatibility findings, documentation improvements, and focused pull requests are welcome. For code changes:

1. Keep HyDE-owned files untouched and preserve unrelated user configuration.
2. Add or update tests for behavioral changes.
3. Run the validation commands above.
4. Explain any new command execution, stored data, or permissions in the pull request.

When reporting a bug, include the relevant component versions and sanitized logs. Do not attach a screen-time database or other private usage data.

## Acknowledgements

Built for the ecosystems created by [HyDE](https://github.com/HyDE-Project/HyDE), [Hyprland](https://hypr.land/), [Waybar](https://github.com/Alexays/Waybar), [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/), and [nwg-displays](https://github.com/nwg-piotr/nwg-displays).

The Waybar integration follows HyDE's documented user module and user layout convention.

## License

[MIT](LICENSE)
