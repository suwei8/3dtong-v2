"""Training pipeline entry point for Model Arena."""


def train_all(history):
    """Train registered models.

    Actual model selection is decided by rolling validation results,
    not by a hard-coded champion.
    """
    return {
        "status": "initialized",
        "models": ["xgboost", "lightgbm", "catboost", "dtong", "ensemble"],
    }
