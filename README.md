# HyDE Display Settings

A small native settings app for HyDE and Hyprland. It brings monitor layout, brightness, night light, idle actions, and private local screen-time statistics into one place. The installer also adds today's screen time to Waybar.

## Requirements

- Python 3.11+
- GTK 4, libadwaita, and PyGObject
- Hyprland, hypridle, hyprlock, hyprsunset, brightnessctl
- nwg-displays (optional monitor layout editor)

On Arch Linux these are available as `python-gobject gtk4 libadwaita hypridle hyprlock hyprsunset brightnessctl nwg-displays`.

## Run

```sh
./hyde-display-settings
```

## Install for the current user

```sh
./install.sh
```

This installs the launcher, desktop entry, and local screen-time service under `~/.local`. Screen-time data never leaves the computer and contains only app class, date, and active seconds.

The Waybar integration follows HyDE's user-module convention:

- Module definition: `~/.config/waybar/modules/custom-display-settings.jsonc`
- Persistent layout: `~/.config/waybar/layouts/display-settings.jsonc`
- Click the module to open Display Settings

The installer backs up the active Waybar config, asks HyDE to regenerate module includes, and reloads Waybar. It never edits HyDE-owned files under `~/.local/share/waybar`.

## Test

```sh
python -m unittest discover -v
```

GitHub Actions runs compilation and unit tests for every push and pull request.

## Uninstall

```sh
./uninstall.sh
```

User settings and screen-time history are intentionally preserved.

## Configuration safety

Applying idle settings writes `~/.config/hypr/hypridle.conf`. A timestamped copy is saved beside it first. Night-light settings use `~/.config/hypr/hyprsunset.conf` with the same backup behavior.

## License

MIT
