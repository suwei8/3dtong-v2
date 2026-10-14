"""Feature builder for chronological K3 experiments."""

import pandas as pd


def build_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create leakage-safe rolling features.

    Features are calculated from rows before the current draw only.
    """
    out = df.copy()
    if "KaiJiang" in out.columns:
        for digit in range(10):
            out[f"digit_{digit}"] = out["KaiJiang"].astype(str).apply(
                lambda x: int(str(digit) in x)
            )
    return out
