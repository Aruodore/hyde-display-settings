import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from row_registry import RowRegistry


class RowRegistryTests(unittest.TestCase):
    def test_clear_removes_each_row_from_the_group_that_added_it(self) -> None:
        first_group = Mock()
        second_group = Mock()
        first_row = object()
        second_row = object()
        registry = RowRegistry()
        registry.track(first_group, first_row)
        registry.track(second_group, second_row)

        registry.clear()

        first_group.remove.assert_called_once_with(first_row)
        second_group.remove.assert_called_once_with(second_row)
        self.assertEqual(len(registry), 0)

    def test_repeated_clear_does_not_remove_rows_twice(self) -> None:
        group = Mock()
        registry = RowRegistry()
        registry.track(group, object())
        registry.clear()
        registry.clear()
        group.remove.assert_called_once()


if __name__ == "__main__":
    unittest.main()
