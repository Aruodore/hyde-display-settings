def stepped_value(value: int, delta: int, minimum: int = 1, maximum: int = 240) -> int:
    return min(maximum, max(minimum, value + delta))
