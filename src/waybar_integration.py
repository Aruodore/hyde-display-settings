from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

MODULE_NAME = "custom/display-settings"


def add_module(config: str) -> str:
    if f'"{MODULE_NAME}"' in config:
        return config
    backlight = re.search(r'(?m)^(\s*)"backlight"\s*,?', config)
    if backlight:
        indent = backlight.group(1)
        line_end = config.find("\n", backlight.end())
        line_end = len(config) if line_end < 0 else line_end
        existing = config[backlight.start():line_end]
        if not existing.rstrip().endswith(","):
            existing = existing.rstrip() + ","
        replacement = f'{existing}\n{indent}"{MODULE_NAME}",'
        return config[:backlight.start()] + replacement + config[line_end:]
    group = re.search(r'(?s)("group/pill#right1"\s*:\s*\{.*?"modules"\s*:\s*\[)(.*?)(\])', config)
    if group:
        indent_match = re.search(r"\n(\s*)\S", group.group(2))
        indent = indent_match.group(1) if indent_match else "            "
        body = group.group(2).rstrip()
        if body and not body.endswith(","):
            body += ","
        body += f'\n{indent}"{MODULE_NAME}"\n        '
        return config[:group.start(2)] + body + config[group.end(2):]
    raise ValueError("Could not find a suitable modules group in the Waybar layout")


def remove_module(config: str) -> str:
    pattern = rf'(?m)^\s*"{re.escape(MODULE_NAME)}"\s*,?\s*\n?'
    return re.sub(pattern, "", config)


def write_with_backup(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, path.with_name(f"{path.name}.backup-{stamp}"))
    path.write_text(content)


def regenerate_waybar() -> None:
    candidates = [
        shutil.which("waybar.py"),
        str(Path.home() / ".local/lib/hyde/waybar.py"),
    ]
    tool = next((item for item in candidates if item and Path(item).exists()), None)
    if tool:
        subprocess.run([tool, "--generate-includes"], check=False)
    subprocess.run(["pkill", "-SIGUSR2", "waybar"], check=False)


def install(config_home: Path, module_source: Path) -> None:
    waybar = config_home / "waybar"
    active = waybar / "config.jsonc"
    if not active.exists():
        raise FileNotFoundError(f"Waybar config not found: {active}")
    module_target = waybar / "modules/custom-display-settings.jsonc"
    module_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(module_source, module_target)
    patched = add_module(active.read_text())
    write_with_backup(active, patched)
    write_with_backup(waybar / "layouts/display-settings.jsonc", patched)


def uninstall(config_home: Path) -> None:
    waybar = config_home / "waybar"
    (waybar / "modules/custom-display-settings.jsonc").unlink(missing_ok=True)
    for path in (waybar / "config.jsonc", waybar / "layouts/display-settings.jsonc"):
        if path.exists():
            write_with_backup(path, remove_module(path.read_text()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the HyDE Display Settings Waybar module")
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--config-home", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
    parser.add_argument("--module", type=Path)
    args = parser.parse_args()
    if args.action == "install":
        if not args.module:
            parser.error("--module is required when installing")
        install(args.config_home, args.module)
    else:
        uninstall(args.config_home)
    regenerate_waybar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
