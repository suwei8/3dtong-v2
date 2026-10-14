from dataclasses import dataclass

@dataclass
class ClineMimoPredictor:
    model: str = "cline-free/mimo-v2.6-flash"

    def build_prompt(self, summary: str) -> str:
        return f"Analyze k3 prediction context and return three candidate digits.\n{summary}"

    def predict(self, summary: str):
        return {"model": self.model, "status": "adapter-ready", "prompt": self.build_prompt(summary)}
