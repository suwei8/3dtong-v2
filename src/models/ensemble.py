"""Ensemble is scored independently; not presumed to beat individual challengers."""
import numpy as np
def mean_proba(predictions):
    if not predictions:
        raise ValueError("no model probability arrays")
    values=list(predictions.values())
    if len({v.shape for v in values})!=1:
        raise ValueError("prediction array shape mismatch")
    return np.mean(values,axis=0)
