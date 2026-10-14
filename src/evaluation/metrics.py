def hit_any_digit(predicted, actual):
    """Return whether prediction hits any actual digit."""
    return bool(set(predicted) & set(actual))


def hit_count(predicted, actual):
    return len(set(predicted) & set(actual))
