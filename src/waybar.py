from __future__ import annotations

import html
import json
import sqlite3
from contextlib import closing
from datetime import date

from analytics import comparison_text, week_analysis
from tracker import DB_PATH


def compact_duration(seconds: int) -> str:
    minutes = max(0, seconds) // 60
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes}m"


def usage_today() -> tuple[int, list[tuple[str, int]]]:
    if not DB_PATH.exists():
        return 0, []
    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            day = date.today().isoformat()
            total = connection.execute(
                "SELECT COALESCE(SUM(seconds), 0) FROM usage WHERE day = ?", (day,)
            ).fetchone()[0]
            apps = connection.execute(
                "SELECT app, seconds FROM usage WHERE day = ? ORDER BY seconds DESC LIMIT 5", (day,)
            ).fetchall()
            return int(total), [(str(app), int(seconds)) for app, seconds in apps]
    except sqlite3.Error:
        return 0, []


def payload(total: int, apps: list[tuple[str, int]], week_total: int = 0, comparison: str = "") -> dict[str, str]:
    text = "󰍹" if total < 60 else f"󰍹 {compact_duration(total)}"
    if not apps:
        tooltip = "Screen time: no activity recorded today\nClick to open Display Settings"
    else:
        lines = [f"Today: {compact_duration(total)}"]
        if week_total:
            lines.extend([f"This week: {compact_duration(week_total)}", comparison, ""])
        lines.extend(f"{html.escape(app)}: {compact_duration(seconds)}" for app, seconds in apps)
        lines.append("\nClick to open Display Settings")
        tooltip = "\n".join(lines)
    return {"text": text, "tooltip": tooltip, "class": "active" if total else "empty"}


def main() -> int:
    total, apps = usage_today()
    analysis = week_analysis(DB_PATH)
    comparison = comparison_text(analysis.change_percent, analysis.last_week)
    print(json.dumps(payload(total, apps, analysis.this_week, comparison), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
