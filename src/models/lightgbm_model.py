"""LightGBM predictor adapter."""


class LightGBMPredictor:
    name = "lightgbm"

    def fit(self, X, y):
        self.model = None
        return self

    def predict(self, X):
        return {"model": self.name, "digits": []}
