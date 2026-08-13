from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

MODULE_NAME = "custom/display-settings"


@dataclass
class JsonNode:
    kind: str
    start: int
    end: int
    value: object = None
    properties: dict[str, "JsonNode"] = field(default_factory=dict)
    items: list["JsonNode"] = field(default_factory=list)


def jsonc_tokens(config: str) -> list[tuple[str, object, int, int]]:
    tokens: list[tuple[str, object, int, int]] = []
    index = 0
    while index < len(config):
        if config[index].isspace():
            index += 1
        elif config.startswith("//", index):
            newline = config.find("\n", index + 2)
            index = len(config) if newline < 0 else newline + 1
        elif config.startswith("/*", index):
            end = config.find("*/", index + 2)
            if end < 0:
                raise ValueError("Unterminated JSONC comment")
            index = end + 2
        elif config[index] == '"':
            start = index
            index += 1
            while index < len(config):
                if config[index] == "\\":
                    index += 2
                elif config[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise ValueError("Unterminated JSONC string")
            tokens.append(("string", json.loads(config[start:index]), start, index))
        elif config[index] in "{}[]:,":
            tokens.append((config[index], config[index], index, index + 1))
            index += 1
        else:
            start = index
            while index < len(config) and not config[index].isspace() and config[index] not in "{}[]:,":
                index += 1
            tokens.append(("literal", config[start:index], start, index))
    return tokens


def parse_jsonc(config: str) -> tuple[JsonNode, list[tuple[str, object, int, int]]]:
    tokens = jsonc_tokens(config)

    def parse(position: int) -> tuple[JsonNode, int]:
        if position >= len(tokens):
            raise ValueError("Unexpected end of JSONC")
        kind, value, start, end = tokens[position]
        if kind == "{":
            node = JsonNode("object", start, end)
            position += 1
            while position < len(tokens) and tokens[position][0] != "}":
                if tokens[position][0] != "string" or position + 1 >= len(tokens) or tokens[position + 1][0] != ":":
                    raise ValueError("Malformed JSONC object")
                key = str(tokens[position][1])
                child, position = parse(position + 2)
                node.properties[key] = child
                if position < len(tokens) and tokens[position][0] == ",":
                    position += 1
                elif position < len(tokens) and tokens[position][0] != "}":
                    raise ValueError("Missing comma in JSONC object")
            if position >= len(tokens):
                raise ValueError("Unterminated JSONC object")
            node.end = tokens[position][3]
            return node, position + 1
        if kind == "[":
            node = JsonNode("array", start, end)
            position += 1
            while position < len(tokens) and tokens[position][0] != "]":
                child, position = parse(position)
                node.items.append(child)
                if position < len(tokens) and tokens[position][0] == ",":
                    position += 1
                elif position < len(tokens) and tokens[position][0] != "]":
                    raise ValueError("Missing comma in JSONC array")
            if position >= len(tokens):
                raise ValueError("Unterminated JSONC array")
            node.end = tokens[position][3]
            return node, position + 1
        if kind == "literal":
            try:
                value = json.loads(str(value))
            except ValueError as error:
                raise ValueError("Invalid JSONC literal") from error
        return JsonNode(kind, start, end, value=value), position + 1

    root, position = parse(0)
    if position != len(tokens):
        raise ValueError("Unexpected content after JSONC document")
    return root, tokens


def module_array(config: str) -> tuple[JsonNode, list[tuple[str, object, int, int]]]:
    root, tokens = parse_jsonc(config)
    if root.kind != "object":
        raise ValueError("Waybar config must be an object")
    group = root.properties.get("group/pill#right1")
    target = group.properties.get("modules") if group and group.kind == "object" else None
    target = target or root.properties.get("modules-right")
    if not target or target.kind != "array":
        raise ValueError("Could not find a suitable modules group in the Waybar layout")
    return target, tokens


def add_module(config: str) -> str:
    target, tokens = module_array(config)
    if any(item.kind == "string" and item.value == MODULE_NAME for item in target.items):
        return config
    close = target.end - 1
    if target.items:
        last = target.items[-1]
        line_start = config.rfind("\n", 0, last.start) + 1
        candidate_indent = config[line_start:last.start]
        indent = candidate_indent if not candidate_indent.strip() else "    "
        trailing_comma = any(kind == "," and start >= last.end and end <= close for kind, _value, start, end in tokens)
        prefix = "" if trailing_comma else ","
        insertion = f'{prefix}\n{indent}"{MODULE_NAME}"'
    else:
        line_start = config.rfind("\n", 0, target.start) + 1
        indent = config[line_start:target.start] + "    "
        insertion = f'\n{indent}"{MODULE_NAME}"\n{config[line_start:target.start]}'
    return config[:close] + insertion + config[close:]


def remove_module(config: str) -> str:
    target, tokens = module_array(config)
    for index, item in enumerate(target.items):
        if item.kind != "string" or item.value != MODULE_NAME:
            continue
        following_comma = next(
            (token for token in tokens if token[0] == "," and item.end <= token[2] < target.end),
            None,
        )
        if following_comma:
            return config[:item.start] + config[following_comma[3]:]
        previous_end = target.items[index - 1].end if index else target.start + 1
        preceding_comma = next(
            (token for token in reversed(tokens) if token[0] == "," and previous_end <= token[2] < item.start),
            None,
        )
        if preceding_comma:
            between = config[preceding_comma[3]:item.start]
            if "//" in between or "/*" in between:
                return config[:item.start] + config[item.end:]
            return config[:preceding_comma[2]] + config[item.end:]
        return config[:item.start] + config[item.end:]
    return config


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
    backups = sorted(path.parent.glob(f"{path.name}.backup-*"), key=lambda item: item.name, reverse=True)
    for old_backup in backups[10:]:
        old_backup.unlink(missing_ok=True)


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
