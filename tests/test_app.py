import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from styles import APP_CSS


class AppStyleTests(unittest.TestCase):
    def test_selected_tab_pairs_semantic_accent_colors(self) -> None:
        selected_rule = APP_CSS.split("}", 1)[0]
        self.assertIn(".display-tabs button:checked", selected_rule)
        self.assertIn("background-color: @accent_bg_color", selected_rule)
        self.assertIn("color: @accent_fg_color", selected_rule)

    def test_selected_tab_icon_and_label_use_foreground_color(self) -> None:
        self.assertIn(".display-tabs button:checked label", APP_CSS)
        self.assertIn(".display-tabs button:checked image", APP_CSS)


if __name__ == "__main__":
    unittest.main()
