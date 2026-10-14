from abc import ABC, abstractmethod


class BasePredictor(ABC):
    """Unified predictor interface."""

    name = "base"

    @abstractmethod
    def predict(self, features):
        raise NotImplementedError
