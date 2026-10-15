"""Aggregated, no-raw-row statistics passed to a model contestant."""
from collections import Counter
import json

def summary_for_llm(history):
    if len(history)<100:
        raise ValueError("at least 100 historical results required")
    info={"as_of_issue":history[-1]["Issue"],
          "draws_observed":len(history),
          "presence_counts":{},"missing_streak":{}}
    for window in (10,30,100):
        counts=Counter(d for row in history[-window:] for d in set(row["KaiJiang"]))
        info["presence_counts"][str(window)]={str(d):counts.get(str(d),0) for d in range(10)}
    for d in range(10):
        info["missing_streak"][str(d)]=next(
            (i for i,row in enumerate(reversed(history)) if str(d) in row["KaiJiang"]),200)
    return json.dumps(info,sort_keys=True,separators=(",",":"))
