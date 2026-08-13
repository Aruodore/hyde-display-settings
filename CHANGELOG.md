# Changelog

All notable changes to HyDE Display Settings are documented here.

The project follows [Semantic Versioning](https://semver.org/). Before 1.0,
minor releases may include compatibility changes while the public interface is
still being established.

## [Unreleased]

### Fixed

- Screen Time rows no longer duplicate on each 30-second refresh.

### Planned

- Day and Week screen-time reports with period navigation
- Privacy-preserving hourly activity buckets for future daily charts
- Per-app duration and share for every selected report period

## [0.1.0] - 2026-08-13

### Added

- Native GTK 4 and libadwaita display settings application
- Monitor discovery and visual layout editing through `nwg-displays`
- Brightness control through `brightnessctl`
- Scheduled night-light profiles through `hyprsunset`
- Configurable dim, lock, display-off, and suspend actions through `hypridle`
- Opt-in local screen-time tracking by application class
- Today, current-week, previous-week, daily-average, and top-app analysis
- Clickable HyDE Waybar module with daily and weekly context
- User-local installer, desktop entry, and hardened systemd service
- Managed configuration blocks, timestamped backups, atomic writes, and rollback
- Automated tests and GitHub Actions validation

### Fixed

- Tracker startup before the Hyprland environment reaches the systemd user manager
- Reloading HyDE-managed `hypridle` and `hyprsunset` processes after applying settings
- Invisible native spin-row symbols under icon themes with hard-coded dark SVG fills
- Safe Waybar tooltip escaping and private SQLite file permissions

[Unreleased]: https://github.com/Aruodore/hyde-display-settings/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Aruodore/hyde-display-settings/releases/tag/v0.1.0
