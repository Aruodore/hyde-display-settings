import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from controls import stepped_value


class TimeoutControlTests(unittest.TestCase):
    def test_stepper_increases_and_decreases(self) -> None:
        self.assertEqual(stepped_value(10, 1), 11)
        self.assertEqual(stepped_value(10, -1), 9)

    def test_stepper_stays_within_timeout_bounds(self) -> None:
        self.assertEqual(stepped_value(1, -1), 1)
        self.assertEqual(stepped_value(240, 1), 240)


if __name__ == "__main__":
    unittest.main()
