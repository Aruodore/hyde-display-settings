from __future__ import annotations

import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from waybar import compact_duration, payload
from waybar_integration import MODULE_NAME, add_module, remove_module


SAMPLE = '''{
    "group/pill#right1": {
        "modules": [
            "backlight",
            "network"
        ]
    }
}
'''


class WaybarTests(unittest.TestCase):
    def test_compact_duration(self) -> None:
        self.assertEqual(compact_duration(59), "0m")
        self.assertEqual(compact_duration(3_600), "1h")
        self.assertEqual(compact_duration(5_460), "1h 31m")

    def test_payload_has_plain_empty_state(self) -> None:
        result = payload(0, [])
        self.assertEqual(result["class"], "empty")
        self.assertIn("no activity", result["tooltip"])

    def test_payload_escapes_pango_markup(self) -> None:
        result = payload(60, [("<b>spoof</b>", 60)])
        self.assertNotIn("<b>", result["tooltip"])
        self.assertIn("&lt;b&gt;", result["tooltip"])

    def test_add_module_after_backlight(self) -> None:
        patched = add_module(SAMPLE)
        self.assertIn(f'"{MODULE_NAME}"', patched)
        self.assertLess(patched.index('"backlight"'), patched.index(f'"{MODULE_NAME}"'))

    def test_add_module_is_idempotent(self) -> None:
        once = add_module(SAMPLE)
        self.assertEqual(add_module(once), once)

    def test_remove_module_preserves_other_modules(self) -> None:
        result = remove_module(add_module(SAMPLE))
        self.assertNotIn(MODULE_NAME, result)
        self.assertIn('"network"', result)

    def test_module_definition_is_not_mistaken_for_layout_item(self) -> None:
        config = '''{
  "backlight": { "format": "x" },
  "modules-right": [
    "backlight"
  ]
}
'''
        result = add_module(config)
        self.assertIn('"backlight": { "format": "x" }', result)
        self.assertIn(f'"{MODULE_NAME}"', result)

    def test_layout_without_backlight_is_supported(self) -> None:
        config = '{\n  "modules-right": [\n    "clock"\n  ]\n}\n'
        self.assertIn(MODULE_NAME, add_module(config))


if __name__ == "__main__":
    unittest.main()
