from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

APP_ID = "io.github.coding_this.HyDEDisplaySettings"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "hyde-display-settings"
APP_CONFIG = CONFIG_DIR / "hyde-display-settings/settings.json"
HYPRIDLE_CONFIG = CONFIG_DIR / "hypr/hypridle.conf"
HYPRSUNSET_CONFIG = CONFIG_DIR / "hypr/hyprsunset.conf"


@dataclass
class Settings:
    dim_minutes: int = 9
    lock_minutes: int = 10
    display_off_minutes: int = 15
    suspend_minutes: int = 20
    dim_enabled: bool = True
    lock_enabled: bool = True
    display_off_enabled: bool = True
    suspend_enabled: bool = True
    night_light_enabled: bool = False
    night_temperature: int = 4500
    night_start: str = "21:00"
    night_end: str = "06:00"
    tracking_enabled: bool = False

    @classmethod
    def validated(cls, raw: object) -> "Settings":
        defaults = cls()
        if not isinstance(raw, dict):
            raise ValueError("settings must be a JSON object")
        values: dict[str, object] = {}
        minute_fields = ("dim_minutes", "lock_minutes", "display_off_minutes", "suspend_minutes")
        boolean_fields = (
            "dim_enabled", "lock_enabled", "display_off_enabled", "suspend_enabled",
            "night_light_enabled", "tracking_enabled",
        )
        for field in minute_fields:
            value = raw.get(field, getattr(defaults, field))
            values[field] = value if type(value) is int and 1 <= value <= 240 else getattr(defaults, field)
        for field in boolean_fields:
            value = raw.get(field, getattr(defaults, field))
            values[field] = value if type(value) is bool else getattr(defaults, field)
        temperature = raw.get("night_temperature", defaults.night_temperature)
        values["night_temperature"] = temperature if type(temperature) is int and 2500 <= temperature <= 6500 else defaults.night_temperature
        for field in ("night_start", "night_end"):
            value = raw.get(field, getattr(defaults, field))
            values[field] = value if isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) else getattr(defaults, field)
        return cls(**values)

    @classmethod
    def load(cls) -> "Settings":
        try:
            raw = json.loads(APP_CONFIG.read_text())
            return cls.validated(raw)
        except (OSError, ValueError, TypeError, AttributeError):
            return cls.from_existing_configs()

    @classmethod
    def from_existing_configs(cls) -> "Settings":
        value = cls()
        try:
            timeouts = [int(item) for item in re.findall(r"(?m)^\s*timeout\s*=\s*(\d+)", HYPRIDLE_CONFIG.read_text())]
            for field, seconds in zip(("dim_minutes", "lock_minutes", "display_off_minutes", "suspend_minutes"), timeouts):
                setattr(value, field, min(240, max(1, round(seconds / 60))))
        except OSError:
            pass
        return value

    def save(self) -> None:
        APP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        APP_CONFIG.parent.chmod(0o700)
        atomic_write(APP_CONFIG, json.dumps(asdict(self), indent=2) + "\n")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = path.with_name(f"{path.name}.backup-{stamp}")
        shutil.copy2(path, backup)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def idle_listeners(settings: Settings) -> str:
    blocks: list[str] = []
    if settings.dim_enabled:
        blocks.append(f"""listener {{
    timeout = {settings.dim_minutes * 60}
    on-timeout = brightnessctl -s && brightnessctl set 1%
    on-resume = brightnessctl -r
}}""")
    if settings.lock_enabled:
        blocks.append(f"""listener {{
    timeout = {settings.lock_minutes * 60}
    on-timeout = loginctl lock-session
}}""")
    if settings.display_off_enabled:
        blocks.append(f"""listener {{
    timeout = {settings.display_off_minutes * 60}
    on-timeout = hyprctl dispatch dpms off
    on-resume = hyprctl dispatch dpms on
}}""")
    if settings.suspend_enabled:
        blocks.append(f"""listener {{
    timeout = {settings.suspend_minutes * 60}
    on-timeout = systemctl suspend
}}""")
    listeners = "\n\n".join(blocks)
    return listeners


IDLE_START = "# BEGIN HYDE DISPLAY SETTINGS"
IDLE_END = "# END HYDE DISPLAY SETTINGS"


def replace_managed_block(existing: str, body: str, start: str = IDLE_START, end: str = IDLE_END) -> str:
    block = f"{start}\n{body.rstrip()}\n{end}"
    pattern = re.compile(rf"(?ms)^\s*{re.escape(start)}.*?^\s*{re.escape(end)}\s*")
    if pattern.search(existing):
        return pattern.sub(block + "\n", existing, count=1)
    return existing.rstrip() + "\n\n" + block + "\n"


def idle_config(settings: Settings, existing: str = "") -> str:
    if not existing.strip():
        existing = """# Hypridle configuration
$LOCKSCREEN = hyde-shell lockscreen

general {
    lock_cmd = $LOCKSCREEN
    before_sleep_cmd = loginctl lock-session
    ignore_dbus_inhibit = false
    ignore_systemd_inhibit = false
}
"""
    if IDLE_START not in existing:
        listener = re.compile(r"(?ms)^\s*listener\s*\{.*?^\s*\}\s*")
        existing = listener.sub(lambda match: "" if is_legacy_hyde_listener(match.group(0)) else match.group(0), existing)
    return replace_managed_block(existing, idle_listeners(settings))


def is_legacy_hyde_listener(block: str) -> bool:
    commands: list[tuple[str, str]] = []
    for key, value in re.findall(r"(?m)^\s*(on-timeout|on-resume)\s*=\s*(.*?)\s*$", block):
        value = value.split("#", 1)[0].strip().strip("{} ").strip().rstrip(";").strip()
        commands.append((key, re.sub(r"\s+", " ", value)))
    known = {
        ("on-timeout", "brightnessctl -s && brightnessctl s 1%"),
        ("on-timeout", "brightnessctl -s && brightnessctl set 1%"),
        ("on-timeout", "brightnessctl set 1%"),
        ("on-resume", "brightnessctl -r"),
        ("on-timeout", "loginctl lock-session"),
        ("on-timeout", "hyprctl dispatch dpms off"),
        ("on-resume", "hyprctl dispatch dpms on"),
        ("on-timeout", "systemctl suspend"),
    }
    return bool(commands) and all(command in known for command in commands)


def sunset_config(settings: Settings, existing: str = "") -> str:
    if not settings.night_light_enabled:
        body = "# Night light is disabled."
    else:
        body = f"""profile {{
    time = {settings.night_end}
    identity = true
}}

profile {{
    time = {settings.night_start}
    temperature = {settings.night_temperature}
}}"""
    return replace_managed_block(existing, body)


def run_quiet(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def restart_process(name: str, command: list[str]) -> None:
    # HyDE normally launches these helpers directly rather than through their
    # optional systemd units. Stop that unmanaged process before asking
    # systemd to start a fresh instance with the newly written configuration.
    run_quiet("pkill", "-x", name)
    service = run_quiet("systemctl", "--user", "restart", f"{name}.service")
    if service.returncode == 0:
        return
    if shutil.which(command[0]) and shutil.which("hyprctl"):
        run_quiet("hyprctl", "dispatch", "exec", " ".join(command))


def apply_settings(settings: Settings) -> None:
    idle_existing = HYPRIDLE_CONFIG.read_text() if HYPRIDLE_CONFIG.exists() else ""
    sunset_existing = HYPRSUNSET_CONFIG.read_text() if HYPRSUNSET_CONFIG.exists() else ""
    app_existing = APP_CONFIG.read_text() if APP_CONFIG.exists() else ""
    idle_new = idle_config(settings, idle_existing)
    sunset_new = sunset_config(settings, sunset_existing)
    try:
        atomic_write(HYPRIDLE_CONFIG, idle_new)
        atomic_write(HYPRSUNSET_CONFIG, sunset_new)
        settings.save()
    except OSError:
        if idle_existing:
            atomic_write(HYPRIDLE_CONFIG, idle_existing)
        else:
            HYPRIDLE_CONFIG.unlink(missing_ok=True)
        if sunset_existing:
            atomic_write(HYPRSUNSET_CONFIG, sunset_existing)
        else:
            HYPRSUNSET_CONFIG.unlink(missing_ok=True)
        if app_existing:
            atomic_write(APP_CONFIG, app_existing)
        else:
            APP_CONFIG.unlink(missing_ok=True)
        raise
    restart_process("hypridle", ["hypridle"])
    restart_process("hyprsunset", ["hyprsunset", "-c", str(HYPRSUNSET_CONFIG)])
