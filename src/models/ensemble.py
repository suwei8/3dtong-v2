"""Model competition ensemble."""


def rank_predictions(results):
    """Combine model outputs without assuming a champion."""
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
