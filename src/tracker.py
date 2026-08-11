from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import time
from datetime import date
from pathlib import Path

from settings import STATE_DIR, Settings

DB_PATH = STATE_DIR / "screen-time.sqlite3"
RUNNING = True


def stop(*_args: object) -> None:
    global RUNNING
    RUNNING = False


def database() -> sqlite3.Connection:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.chmod(0o700)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS usage (day TEXT NOT NULL, app TEXT NOT NULL, seconds INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(day, app))"
    )
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{DB_PATH}{suffix}")
        if path.exists():
            path.chmod(0o600)
    return connection


def session_is_active() -> bool:
    session_id = os.environ.get("XDG_SESSION_ID", "self")
    session = subprocess.run(
        ["loginctl", "show-session", session_id, "--property=LockedHint", "--property=IdleHint"],
        text=True, capture_output=True, timeout=3, check=False,
    )
    state = session.stdout.lower()
    if session.returncode == 0 and ("lockedhint=yes" in state or "idlehint=yes" in state):
        return False
    monitors = subprocess.run(["hyprctl", "monitors", "-j"], text=True, capture_output=True, timeout=3, check=False)
    if monitors.returncode == 0:
        try:
            values = json.loads(monitors.stdout)
            if values and not any(item.get("dpmsStatus", True) for item in values):
                return False
        except (ValueError, TypeError):
            pass
    idle = subprocess.run(
        ["busctl", "--user", "call", "org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver", "GetSessionIdleTime"],
        text=True, capture_output=True, timeout=3, check=False,
    )
    if idle.returncode == 0:
        try:
            return int(idle.stdout.split()[-1]) < 60_000
        except (ValueError, IndexError):
            pass
    return True


def active_app() -> str | None:
    result = subprocess.run(["hyprctl", "activewindow", "-j"], text=True, capture_output=True, timeout=3, check=False)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
        app = str(payload.get("initialClass") or payload.get("class") or "").strip()
        return app[:120] or None
    except (ValueError, TypeError):
        return None


def record(connection: sqlite3.Connection, app: str, seconds: int) -> None:
    connection.execute(
        "INSERT INTO usage(day, app, seconds) VALUES(?, ?, ?) ON CONFLICT(day, app) DO UPDATE SET seconds = seconds + excluded.seconds",
        (date.today().isoformat(), app, seconds),
    )
    connection.commit()


def main() -> int:
    os.umask(0o077)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    connection = database()
    last_tick = time.monotonic()
    while RUNNING:
        settings = Settings.load()
        now = time.monotonic()
        elapsed = min(15, max(0, round(now - last_tick)))
        last_tick = now
        if settings.tracking_enabled:
            try:
                app = active_app() if session_is_active() else None
                if app and elapsed:
                    record(connection, app, elapsed)
            except (OSError, sqlite3.Error, subprocess.SubprocessError):
                pass
        time.sleep(5)
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
