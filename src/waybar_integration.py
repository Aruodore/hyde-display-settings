from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

MODULE_NAME = "custom/display-settings"


def add_module(config: str) -> str:
    if f'"{MODULE_NAME}"' in config:
        return config
    group_start = config.find('"group/pill#right1"')
    search_start = group_start if group_start >= 0 else 0
    key = '"modules"' if group_start >= 0 else '"modules-right"'
    key_start = config.find(key, search_start)
    if key_start < 0:
        raise ValueError("Could not find a suitable modules group in the Waybar layout")
    array_start = config.find("[", key_start)
    array_end = config.find("]", array_start)
    if array_start < 0 or array_end < 0:
        raise ValueError("Waybar module array is malformed")
    body = config[array_start + 1:array_end]
    item = re.search(r'(?m)^(\s*)"backlight"\s*,?', body)
    indent_match = re.search(r"\n(\s*)\S", body)
    indent = item.group(1) if item else (indent_match.group(1) if indent_match else "        ")
    if item:
        line_end = body.find("\n", item.end())
        line_end = len(body) if line_end < 0 else line_end
        existing = body[item.start():line_end].rstrip()
        if not existing.endswith(","):
            existing += ","
        body = body[:item.start()] + existing + f'\n{indent}"{MODULE_NAME}",' + body[line_end:]
    else:
        stripped = body.rstrip()
        if stripped and not stripped.endswith(","):
            stripped += ","
        body = stripped + f'\n{indent}"{MODULE_NAME}"\n'
    return config[:array_start + 1] + body + config[array_end:]


def remove_module(config: str) -> str:
    pattern = rf'(?m)^\s*"{re.escape(MODULE_NAME)}"\s*,?\s*\n?'
    return re.sub(pattern, "", config)


def write_with_backup(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(path, path.with_name(f"{path.name}.backup-{stamp}"))
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


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
    parser.add_argument("action", choices=("check", "install", "uninstall"))
    parser.add_argument("--config-home", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
    parser.add_argument("--module", type=Path)
    args = parser.parse_args()
    if args.action in ("check", "install"):
        if not args.module:
            parser.error("--module is required when installing")
        active = args.config_home / "waybar/config.jsonc"
        if not active.exists():
            raise FileNotFoundError(f"Waybar config not found: {active}")
        add_module(active.read_text())
        if not args.module.is_file():
            raise FileNotFoundError(f"Waybar module not found: {args.module}")
        if args.action == "install":
            install(args.config_home, args.module)
    else:
        uninstall(args.config_home)
    if args.action != "check":
        regenerate_waybar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
