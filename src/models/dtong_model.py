from dataclasses import dataclass

@dataclass
class DTongPredictor:
    name: str = "dtong-rule"

    def predict(self, context):
        digits = context.get("digits", [])[:3]
        return {"model": self.name, "digits": digits}
