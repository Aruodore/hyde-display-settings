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

APP_ID = "io.github.hyde.DisplaySettings"
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
    tracking_enabled: bool = True

    @classmethod
    def load(cls) -> "Settings":
        try:
            raw = json.loads(APP_CONFIG.read_text())
            allowed = cls.__dataclass_fields__.keys()
            return cls(**{key: value for key, value in raw.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return cls.from_existing_configs()

    @classmethod
    def from_existing_configs(cls) -> "Settings":
        value = cls()
        try:
            timeouts = [int(item) for item in re.findall(r"(?m)^\s*timeout\s*=\s*(\d+)", HYPRIDLE_CONFIG.read_text())]
            for field, seconds in zip(("dim_minutes", "lock_minutes", "display_off_minutes", "suspend_minutes"), timeouts):
                setattr(value, field, max(1, round(seconds / 60)))
        except OSError:
            pass
        return value

    def save(self) -> None:
        APP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(APP_CONFIG, json.dumps(asdict(self), indent=2) + "\n")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
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


def idle_config(settings: Settings) -> str:
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
    return f"""# Managed by HyDE Display Settings.
# Previous versions are saved beside this file before each change.
$LOCKSCREEN = pidof hyprlock || hyprlock

general {{
    lock_cmd = $LOCKSCREEN
    before_sleep_cmd = loginctl lock-session
    ignore_dbus_inhibit = false
    ignore_systemd_inhibit = false
}}

{listeners}
"""


def sunset_config(settings: Settings) -> str:
    if not settings.night_light_enabled:
        return "# Managed by HyDE Display Settings.\n# Night light is disabled.\n"
    return f"""# Managed by HyDE Display Settings.
profile {{
    time = {settings.night_end}
    identity = true
}}

profile {{
    time = {settings.night_start}
    temperature = {settings.night_temperature}
}}
"""


def run_quiet(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=False)


def restart_process(name: str, command: list[str]) -> None:
    run_quiet("pkill", "-x", name)
    if shutil.which(command[0]):
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def apply_settings(settings: Settings) -> None:
    settings.save()
    atomic_write(HYPRIDLE_CONFIG, idle_config(settings))
    atomic_write(HYPRSUNSET_CONFIG, sunset_config(settings))
    restart_process("hypridle", ["hypridle"])
    restart_process("hyprsunset", ["hyprsunset", "-c", str(HYPRSUNSET_CONFIG)])
