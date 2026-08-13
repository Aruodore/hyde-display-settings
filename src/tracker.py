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
HEALTH_PATH = STATE_DIR / "tracker-health.json"
RUNNING = True


class TrackerUnavailable(RuntimeError):
    pass


def hyprland_environment() -> dict[str, str]:
    environment = os.environ.copy()
    signature = environment.get("HYPRLAND_INSTANCE_SIGNATURE")
    if signature:
        return environment
    runtime = Path(environment.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "hypr"
    candidates = sorted(
        (path for path in runtime.iterdir() if (path / ".socket.sock").exists()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if runtime.is_dir() else []
    if candidates:
        environment["HYPRLAND_INSTANCE_SIGNATURE"] = candidates[0].name
    return environment


def hyprctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["hyprctl", *args], text=True, capture_output=True, timeout=3,
        check=False, env=hyprland_environment(),
    )


def stop(*_args: object) -> None:
    global RUNNING
    RUNNING = False


def database() -> sqlite3.Connection:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.chmod(0o700)
    connection = sqlite3.connect(DB_PATH, timeout=1)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS usage (day TEXT NOT NULL, app TEXT NOT NULL, seconds INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(day, app))"
    )
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{DB_PATH}{suffix}")
        if path.exists():
            path.chmod(0o600)
    return connection


def graphical_session_id() -> str | None:
    session_id = os.environ.get("XDG_SESSION_ID", "").strip()
    if session_id:
        return session_id
    result = subprocess.run(
        ["loginctl", "show-user", str(os.getuid()), "--property=Display", "--value"],
        text=True, capture_output=True, timeout=3, check=False,
    )
    return (result.stdout.strip() or None) if result.returncode == 0 else None


def session_is_active() -> bool:
    session_id = graphical_session_id()
    session_ok = False
    if session_id:
        session = subprocess.run(
            ["loginctl", "show-session", session_id, "--property=LockedHint", "--property=IdleHint"],
            text=True, capture_output=True, timeout=3, check=False,
        )
        session_ok = session.returncode == 0
        state = session.stdout.lower()
        if session_ok and ("lockedhint=yes" in state or "idlehint=yes" in state):
            return False
    monitors = hyprctl("monitors", "-j")
    monitors_ok = False
    if monitors.returncode == 0:
        try:
            values = json.loads(monitors.stdout)
            if not isinstance(values, list):
                raise TypeError("monitor response is not a list")
            monitors_ok = True
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
    if session_ok or monitors_ok:
        return True
    raise TrackerUnavailable("Could not verify the graphical session state")


def active_app() -> str | None:
    result = hyprctl("activewindow", "-j")
    if result.returncode != 0:
        raise TrackerUnavailable("Could not read the active Hyprland window")
    try:
        payload = json.loads(result.stdout)
        app = str(payload.get("initialClass") or payload.get("class") or "")
        app = " ".join(app.split())
        return app[:120] or None
    except (ValueError, TypeError) as error:
        raise TrackerUnavailable("Hyprland returned invalid active-window data") from error


def record(connection: sqlite3.Connection, app: str, seconds: int) -> None:
    connection.execute(
        "INSERT INTO usage(day, app, seconds) VALUES(?, ?, ?) ON CONFLICT(day, app) DO UPDATE SET seconds = seconds + excluded.seconds",
        (date.today().isoformat(), app, seconds),
    )
    connection.commit()


def write_health(status: str, message: str = "") -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = HEALTH_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({"status": status, "message": message, "updated_at": int(time.time())}) + "\n")
    temporary.chmod(0o600)
    temporary.replace(HEALTH_PATH)


def health_error(max_age: int = 30) -> str | None:
    try:
        value = json.loads(HEALTH_PATH.read_text())
        status = value.get("status")
        if status == "error":
            return str(value.get("message") or "Screen-time tracker failed")
        if status == "ok" and int(time.time()) - int(value.get("updated_at", 0)) > max_age:
            return "Screen-time tracker is not responding"
    except (OSError, ValueError, TypeError, AttributeError):
        return "Screen-time tracker has not reported its status"
    return None


def main() -> int:
    os.umask(0o077)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    connection = database()
    last_tick = time.monotonic()
    last_error = ""
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
                write_health("ok")
                last_error = ""
            except (OSError, sqlite3.Error, subprocess.SubprocessError, TrackerUnavailable) as error:
                message = str(error) or type(error).__name__
                write_health("error", message)
                if message != last_error:
                    print(f"screen-time tracker: {message}", file=os.sys.stderr, flush=True)
                    last_error = message
        else:
            write_health("disabled")
        time.sleep(5)
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
