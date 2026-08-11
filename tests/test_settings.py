from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import settings


class SettingsTests(unittest.TestCase):
    def test_idle_config_contains_default_sequence(self) -> None:
        config = settings.idle_config(settings.Settings())
        positions = [config.index(f"timeout = {minutes * 60}") for minutes in (9, 10, 15, 20)]
        self.assertEqual(positions, sorted(positions))

    def test_disabled_idle_action_is_omitted(self) -> None:
        value = settings.Settings(dim_enabled=False)
        self.assertNotIn("brightnessctl", settings.idle_config(value))

    def test_night_light_schedule(self) -> None:
        value = settings.Settings(night_light_enabled=True, night_temperature=3900, night_start="20:30", night_end="06:15")
        config = settings.sunset_config(value)
        self.assertIn("time = 20:30", config)
        self.assertIn("time = 06:15", config)
        self.assertIn("temperature = 3900", config)

    def test_atomic_write_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config"
            target.write_text("old")
            settings.atomic_write(target, "new")
            self.assertEqual(target.read_text(), "new")
            backups = list(target.parent.glob("config.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "old")


if __name__ == "__main__":
    unittest.main()
