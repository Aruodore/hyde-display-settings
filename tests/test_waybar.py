from __future__ import annotations

import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from waybar import compact_duration, payload
from waybar_integration import MODULE_NAME, add_module, parse_jsonc, remove_module


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

    def test_payload_includes_weekly_comparison(self) -> None:
        result = payload(3600, [("kitty", 3600)], 7200, "25% less than last week")
        self.assertIn("This week: 2h", result["tooltip"])
        self.assertIn("25% less than last week", result["tooltip"])

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

    def test_nested_array_is_not_selected_as_module_target(self) -> None:
        config = '{"modules-right":[{"nested":["one","two"]},"clock"]}'
        result = add_module(config)
        self.assertIn('["one","two"]', result)
        self.assertGreater(result.index(MODULE_NAME), result.index('"clock"'))

    def test_module_definition_does_not_count_as_layout_membership(self) -> None:
        config = '{"custom/display-settings":{"exec":"x"},"modules-right":["clock"]}'
        result = add_module(config)
        self.assertEqual(result.count(MODULE_NAME), 2)
        parse_jsonc(result)

    def test_comments_and_trailing_commas_survive_round_trip(self) -> None:
        config = '''{
  // user layout
  "modules-right": [
    "clock", // keep this comment
  ],
}
'''
        result = remove_module(add_module(config))
        parse_jsonc(result)
        self.assertIn("// user layout", result)
        self.assertIn("// keep this comment", result)
        self.assertIn('"clock"', result)


if __name__ == "__main__":
    unittest.main()
