from __future__ import annotations

from typing import Any


class RowRegistry:
    def __init__(self) -> None:
        self._rows: list[tuple[Any, Any]] = []

    def track(self, group: Any, row: Any) -> None:
        self._rows.append((group, row))

    def clear(self) -> None:
        for group, row in self._rows:
            group.remove(row)
        self._rows.clear()

    def __len__(self) -> int:
        return len(self._rows)
