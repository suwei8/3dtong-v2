from datetime import datetime


def run_prediction(models, context):
    result = []
    for model in models:
        result.append(model.predict(context))
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "predictions": result,
    }
