from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import tracker


class TrackerTests(unittest.TestCase):
    def test_database_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            database = state / "usage.sqlite3"
            with patch.object(tracker, "STATE_DIR", state), patch.object(tracker, "DB_PATH", database):
                connection = tracker.database()
                connection.close()
                self.assertEqual(state.stat().st_mode & 0o777, 0o700)
                self.assertEqual(database.stat().st_mode & 0o777, 0o600)

    @patch("tracker.subprocess.run")
    def test_locked_session_is_inactive(self, run) -> None:
        run.return_value = SimpleNamespace(returncode=0, stdout="LockedHint=yes\nIdleHint=no\n")
        self.assertFalse(tracker.session_is_active())

    @patch("tracker.subprocess.run")
    def test_dpms_off_is_inactive(self, run) -> None:
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="LockedHint=no\nIdleHint=no\n"),
            SimpleNamespace(returncode=0, stdout='[{"dpmsStatus": false}]'),
        ]
        self.assertFalse(tracker.session_is_active())

    @patch("tracker.subprocess.run")
    def test_long_idle_session_is_inactive(self, run) -> None:
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="LockedHint=no\nIdleHint=no\n"),
            SimpleNamespace(returncode=0, stdout='[{"dpmsStatus": true}]'),
            SimpleNamespace(returncode=0, stdout="u 60001\n"),
        ]
        self.assertFalse(tracker.session_is_active())


if __name__ == "__main__":
    unittest.main()
