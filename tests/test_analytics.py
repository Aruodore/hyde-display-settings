from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from analytics import comparison_text, week_analysis


class AnalyticsTests(unittest.TestCase):
    def test_week_totals_comparison_days_and_apps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "usage.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE usage(day TEXT, app TEXT, seconds INTEGER)")
                connection.executemany(
                    "INSERT INTO usage VALUES(?, ?, ?)",
                    [
                        ("2026-08-03", "old-app", 3600),
                        ("2026-08-10", "kitty", 1800),
                        ("2026-08-11", "kitty", 1800),
                        ("2026-08-11", "browser", 3600),
                    ],
                )
                connection.commit()
            result = week_analysis(database, date(2026, 8, 11))
            self.assertEqual(result.today, 5400)
            self.assertEqual(result.this_week, 7200)
            self.assertEqual(result.last_week, 3600)
            self.assertEqual(result.previous_period, 3600)
            self.assertEqual(result.daily_average, 3600)
            self.assertEqual(result.change_percent, 100)
            self.assertEqual(result.apps[0], ("kitty", 3600))
            self.assertEqual(len(result.days), 2)

    def test_empty_previous_week_has_clear_comparison(self) -> None:
        self.assertEqual(comparison_text(None, 0), "No activity recorded last week")

    def test_comparison_uses_same_number_of_weekdays(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "usage.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE usage(day TEXT, app TEXT, seconds INTEGER)")
                connection.executemany("INSERT INTO usage VALUES(?, ?, ?)", [
                    ("2026-08-03", "old", 100),
                    ("2026-08-09", "old", 900),
                    ("2026-08-10", "new", 200),
                ])
                connection.commit()
            result = week_analysis(database, date(2026, 8, 10))
            self.assertEqual(result.last_week, 1000)
            self.assertEqual(result.previous_period, 100)
            self.assertEqual(result.change_percent, 100)

    def test_corrupt_database_is_reported_not_shown_as_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "usage.sqlite3"
            database.write_text("not sqlite")
            result = week_analysis(database, date(2026, 8, 10))
            self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
