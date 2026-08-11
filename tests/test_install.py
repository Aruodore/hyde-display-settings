from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class InstallTests(unittest.TestCase):
    def test_waybar_launcher_works_through_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "hyde-display-settings-waybar"
            link.symlink_to(ROOT / "hyde-display-settings-waybar")
            environment = os.environ.copy()
            environment["HYDE_DISPLAY_SETTINGS_HOME"] = str(ROOT)
            result = subprocess.run([link], env=environment, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"text"', result.stdout)


if __name__ == "__main__":
    unittest.main()
