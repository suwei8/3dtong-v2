"""Validate K3 historical datasets used by 3dtong-v2."""

REQUIRED_COLUMNS = {
    "KaiJiang",
    "ShiJiHao",
}


def validate_columns(columns):
    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    return True
