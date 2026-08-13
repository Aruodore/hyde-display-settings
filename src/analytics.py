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
    previous_period: int
    daily_average: int
    change_percent: int | None
    days: list[tuple[date, int]]
    apps: list[tuple[str, int]]
    today_apps: list[tuple[str, int]]
    error: str | None = None


def week_analysis(database: Path, today: date | None = None) -> WeekAnalysis:
    current = today or date.today()
    week_start = current - timedelta(days=current.weekday())
    last_start = week_start - timedelta(days=7)
    last_end = week_start - timedelta(days=1)
    previous_period_end = last_start + timedelta(days=current.weekday())
    days = [(week_start + timedelta(days=offset), 0) for offset in range(current.weekday() + 1)]
    totals: dict[date, int] = {}
    apps: list[tuple[str, int]] = []
    today_apps: list[tuple[str, int]] = []
    last_week = 0
    previous_period = 0
    error: str | None = None

    if database.exists():
        try:
            with closing(sqlite3.connect(database, timeout=0.1)) as connection:
                rows = connection.execute(
                    "SELECT day, app, seconds FROM usage WHERE day BETWEEN ? AND ?",
                    (last_start.isoformat(), current.isoformat()),
                ).fetchall()
                app_totals: dict[str, int] = {}
                today_totals: dict[str, int] = {}
                for day_text, app, seconds in rows:
                    day = date.fromisoformat(str(day_text))
                    value = int(seconds)
                    if day >= week_start:
                        totals[day] = totals.get(day, 0) + value
                        app_name = str(app)
                        app_totals[app_name] = app_totals.get(app_name, 0) + value
                        if day == current:
                            today_totals[app_name] = today_totals.get(app_name, 0) + value
                    elif day <= last_end:
                        last_week += value
                        if day <= previous_period_end:
                            previous_period += value
                apps = sorted(app_totals.items(), key=lambda item: item[1], reverse=True)[:8]
                today_apps = sorted(today_totals.items(), key=lambda item: item[1], reverse=True)[:8]
        except (sqlite3.Error, ValueError, TypeError) as caught:
            error = str(caught) or type(caught).__name__

    days = [(day, totals.get(day, 0)) for day, _seconds in days]
    this_week = sum(seconds for _day, seconds in days)
    elapsed_days = max(1, current.weekday() + 1)
    if previous_period:
        change = round((this_week - previous_period) / previous_period * 100)
    elif this_week:
        change = None
    else:
        change = 0
    return WeekAnalysis(
        today=totals.get(current, 0),
        this_week=this_week,
        last_week=last_week,
        previous_period=previous_period,
        daily_average=round(this_week / elapsed_days),
        change_percent=change,
        days=days,
        apps=apps,
        today_apps=today_apps,
        error=error,
    )


def comparison_text(change: int | None, last_week: int) -> str:
    if last_week == 0:
        return "No activity recorded last week"
    if change == 0:
        return "About the same as last week"
    direction = "more" if change and change > 0 else "less"
    return f"{abs(change or 0)}% {direction} than last week"
