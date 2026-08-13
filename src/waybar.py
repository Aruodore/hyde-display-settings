from __future__ import annotations

import html
import json
from analytics import comparison_text, week_analysis
from settings import Settings
from tracker import DB_PATH, health_error


def compact_duration(seconds: int) -> str:
    minutes = max(0, seconds) // 60
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes}m"


def payload(total: int, apps: list[tuple[str, int]], week_total: int = 0, comparison: str = "", error: str = "") -> dict[str, str]:
    text = "󰍹" if total < 60 else f"󰍹 {compact_duration(total)}"
    if error:
        tooltip = f"Screen-time data unavailable: {html.escape(error)}\nClick to open Display Settings"
    elif not apps:
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
    analysis = week_analysis(DB_PATH)
    comparison = comparison_text(analysis.change_percent, analysis.previous_period)
    tracker_error = health_error() if Settings.load().tracking_enabled else None
    print(json.dumps(payload(analysis.today, analysis.today_apps[:5], analysis.this_week, comparison, analysis.error or tracker_error or ""), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
