from __future__ import annotations

import os
import tempfile
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import tracker


class TrackerTests(unittest.TestCase):
    def test_hyprland_environment_discovers_live_socket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            instance = Path(directory) / "hypr" / "test-signature"
            instance.mkdir(parents=True)
            (instance / ".socket.sock").touch()
            environment = {"XDG_RUNTIME_DIR": directory}
            with patch.dict(os.environ, environment, clear=True):
                result = tracker.hyprland_environment()
            self.assertEqual(result["HYPRLAND_INSTANCE_SIGNATURE"], "test-signature")

    @patch("tracker.subprocess.run")
    @patch("tracker.hyprland_environment", return_value={"HYPRLAND_INSTANCE_SIGNATURE": "live"})
    def test_hyprctl_uses_discovered_environment(self, _environment, run) -> None:
        run.return_value = SimpleNamespace(returncode=0, stdout="{}")
        tracker.hyprctl("activewindow", "-j")
        self.assertEqual(run.call_args.kwargs["env"]["HYPRLAND_INSTANCE_SIGNATURE"], "live")

    def test_database_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            database = state / "usage.sqlite3"
            with patch.object(tracker, "STATE_DIR", state), patch.object(tracker, "DB_PATH", database):
                connection = tracker.database()
                connection.close()
                self.assertEqual(state.stat().st_mode & 0o777, 0o700)
                self.assertEqual(database.stat().st_mode & 0o777, 0o600)

    @patch("tracker.graphical_session_id", return_value="3")
    @patch("tracker.subprocess.run")
    def test_locked_session_is_inactive(self, run, _session) -> None:
        run.return_value = SimpleNamespace(returncode=0, stdout="LockedHint=yes\nIdleHint=no\n")
        self.assertFalse(tracker.session_is_active())

    @patch("tracker.graphical_session_id", return_value="3")
    @patch("tracker.subprocess.run")
    def test_dpms_off_is_inactive(self, run, _session) -> None:
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="LockedHint=no\nIdleHint=no\n"),
            SimpleNamespace(returncode=0, stdout='[{"dpmsStatus": false}]'),
        ]
        self.assertFalse(tracker.session_is_active())

    @patch("tracker.graphical_session_id", return_value="3")
    @patch("tracker.subprocess.run")
    def test_long_idle_session_is_inactive(self, run, _session) -> None:
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="LockedHint=no\nIdleHint=no\n"),
            SimpleNamespace(returncode=0, stdout='[{"dpmsStatus": true}]'),
            SimpleNamespace(returncode=0, stdout="u 60001\n"),
        ]
        self.assertFalse(tracker.session_is_active())

    @patch("tracker.graphical_session_id", return_value=None)
    @patch("tracker.subprocess.run")
    def test_unknown_session_fails_closed(self, run, _session) -> None:
        run.return_value = SimpleNamespace(returncode=1, stdout="")
        with self.assertRaises(tracker.TrackerUnavailable):
            tracker.session_is_active()

    @patch("tracker.hyprctl")
    def test_active_app_strips_control_characters(self, hyprctl) -> None:
        hyprctl.return_value = SimpleNamespace(returncode=0, stdout='{"class":"bad\\napp\\tname"}')
        self.assertEqual(tracker.active_app(), "bad app name")

    def test_stale_health_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            health = Path(directory) / "health.json"
            health.write_text(json.dumps({"status": "ok", "updated_at": 1}))
            with patch.object(tracker, "HEALTH_PATH", health), patch("tracker.time.time", return_value=100):
                self.assertIn("not responding", tracker.health_error(max_age=30))


if __name__ == "__main__":
    unittest.main()
