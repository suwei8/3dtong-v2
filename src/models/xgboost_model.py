"""XGBoost predictor adapter.

Actual training implementation will plug into the common interface.
"""


class XGBoostPredictor:
    name = "xgboost"

    def fit(self, X, y):
        self.model = None
        return self

    def predict(self, X):
        return {"model": self.name, "digits": []}
