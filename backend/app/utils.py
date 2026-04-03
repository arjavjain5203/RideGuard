def normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize value between 0 and 1."""
    if max_val <= min_val:
        return 0.0
    if value <= min_val:
        return 0.0
    if value >= max_val:
        return 1.0
    return (value - min_val) / (max_val - min_val)
