"""Digit overlap is computed on sets; repeated draw digits count once."""
def hit_any_digit(predicted,actual):
    return bool(set(str(d) for d in predicted) & set(str(actual)))

def hit_count(predicted,actual):
    return len(set(str(d) for d in predicted) & set(str(actual)))
