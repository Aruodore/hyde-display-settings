from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import settings


class SettingsTests(unittest.TestCase):
    def test_tracking_is_opt_in(self) -> None:
        self.assertFalse(settings.Settings().tracking_enabled)

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

    def test_idle_config_preserves_unrelated_content(self) -> None:
        existing = "# mine\nlistener {\n timeout = 42\n on-timeout = notify-send custom\n}\n"
        result = settings.idle_config(settings.Settings(), existing)
        self.assertIn("notify-send custom", result)
        self.assertIn(settings.IDLE_START, result)

    def test_managed_block_is_replaced_not_duplicated(self) -> None:
        first = settings.idle_config(settings.Settings(), "# mine\n")
        second = settings.idle_config(settings.Settings(dim_minutes=5), first)
        self.assertEqual(second.count(settings.IDLE_START), 1)
        self.assertIn("timeout = 300", second)

    def test_hyde_default_listeners_are_migrated_without_duplicates(self) -> None:
        existing = """# keep me
listener {
 timeout = 540
 on-timeout = brightnessctl set 1%
}
listener {
 timeout = 77
 on-timeout = notify-send custom
}
"""
        result = settings.idle_config(settings.Settings(), existing)
        self.assertEqual(result.count("timeout = 540"), 1)
        self.assertIn("notify-send custom", result)
        self.assertIn("# keep me", result)

    def test_atomic_write_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config"
            target.write_text("old")
            settings.atomic_write(target, "new")
            self.assertEqual(target.read_text(), "new")
            backups = list(target.parent.glob("config.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), "old")

    def test_apply_rolls_back_when_settings_save_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            idle = root / "hypridle.conf"
            sunset = root / "hyprsunset.conf"
            app_config = root / "settings.json"
            idle.write_text("idle original\n")
            sunset.write_text("sunset original\n")
            app_config.write_text("{}\n")
            with (
                patch.object(settings, "HYPRIDLE_CONFIG", idle),
                patch.object(settings, "HYPRSUNSET_CONFIG", sunset),
                patch.object(settings, "APP_CONFIG", app_config),
                patch.object(settings.Settings, "save", side_effect=OSError("full disk")),
                patch.object(settings, "restart_process"),
            ):
                with self.assertRaises(OSError):
                    settings.apply_settings(settings.Settings())
            self.assertEqual(idle.read_text(), "idle original\n")
            self.assertEqual(sunset.read_text(), "sunset original\n")
            self.assertEqual(app_config.read_text(), "{}\n")


if __name__ == "__main__":
    unittest.main()
