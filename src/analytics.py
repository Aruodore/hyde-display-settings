from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class WeekAnalysis:
    today: int
    this_week: int
    last_week: int
    daily_average: int
    change_percent: int | None
    days: list[tuple[date, int]]
    apps: list[tuple[str, int]]


def week_analysis(database: Path, today: date | None = None) -> WeekAnalysis:
    current = today or date.today()
    week_start = current - timedelta(days=current.weekday())
    last_start = week_start - timedelta(days=7)
    last_end = week_start - timedelta(days=1)
    days = [(week_start + timedelta(days=offset), 0) for offset in range(current.weekday() + 1)]
    totals: dict[date, int] = {}
    apps: list[tuple[str, int]] = []
    last_week = 0

    if database.exists():
        try:
            with closing(sqlite3.connect(database)) as connection:
                for day_text, seconds in connection.execute(
                    "SELECT day, SUM(seconds) FROM usage WHERE day BETWEEN ? AND ? GROUP BY day",
                    (last_start.isoformat(), current.isoformat()),
                ):
                    day = date.fromisoformat(str(day_text))
                    value = int(seconds)
                    if day >= week_start:
                        totals[day] = value
                    elif day <= last_end:
                        last_week += value
                apps = [
                    (str(app), int(seconds))
                    for app, seconds in connection.execute(
                        "SELECT app, SUM(seconds) FROM usage WHERE day BETWEEN ? AND ? "
                        "GROUP BY app ORDER BY SUM(seconds) DESC LIMIT 8",
                        (week_start.isoformat(), current.isoformat()),
                    )
                ]
        except (sqlite3.Error, ValueError):
            pass

    days = [(day, totals.get(day, 0)) for day, _seconds in days]
    this_week = sum(seconds for _day, seconds in days)
    elapsed_days = max(1, current.weekday() + 1)
    if last_week:
        change = round((this_week - last_week) / last_week * 100)
    elif this_week:
        change = None
    else:
        change = 0
    return WeekAnalysis(
        today=totals.get(current, 0),
        this_week=this_week,
        last_week=last_week,
        daily_average=round(this_week / elapsed_days),
        change_percent=change,
        days=days,
        apps=apps,
    )


def comparison_text(change: int | None, last_week: int) -> str:
    if last_week == 0:
        return "No activity recorded last week"
    if change == 0:
        return "About the same as last week"
    direction = "more" if change and change > 0 else "less"
    return f"{abs(change or 0)}% {direction} than last week"
