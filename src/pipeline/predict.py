"""Build sealed, source-cutoff-specific multi-horizon forecasts.

No full-history data or held-out outcomes are consumed by this program.
"""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from src.data.loader import load_history
from src.pipeline.train import train_all

def issue_after(issue,k):
    n=int(issue)
    if k<1 or k>30:
        raise ValueError("horizon out of range")
    # Supported only within issue's current calendar-year sequence.
    if int(issue[-3:])+k>365:
        raise ValueError("year boundary requires next year issue calendar")
    return str(n+k)

def create_prediction(history, source_hash, horizon=10, validation_size=800):
    arena=train_all(history,validation_size)
    latest=history[-1]["Issue"]
    return {
        "schema":1,"type":"fixed-origin historical holdout / future forecast",
        "source":"private pinble-data/data/k3_full_history_test.csv",
        "source_sha256":source_hash,
        "last_known_issue":latest,
        "last_known_draw_count":len(history),
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "selection_policy":"champion selected using historical validation only",
        "validation":arena["scores"],
        "champion_validation_only":arena["champion_validation_only"],
        "note":"The same fixed-origin forecast applies to all horizons. No unknown intervening draws were used.",
        "predictions":[{"issue":issue_after(latest,k),"horizon":k,
                        "models":arena["predictions"]}
                       for k in range(1,horizon+1)]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True)
    p.add_argument("--out",default="predictions")
    p.add_argument("--horizon",type=int,default=10)
    p.add_argument("--validation-size",type=int,default=800)
    a=p.parse_args()
    source=Path(a.history)
    content=source.read_bytes()
    signature=hashlib.sha256(content).hexdigest()
    history=load_history(source)
    target=Path(a.out)/"runs"/f'{history[-1]["Issue"]}-{signature[:12]}.json'
    if target.exists():
        print("prediction already frozen:",target)
        return
    data=create_prediction(history,signature,a.horizon,a.validation_size)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    latest=Path(a.out)/"LATEST.md"
    lines=["# 3dtong-v2 latest forecast","",
           f'Source cutoff: **{data["last_known_issue"]}**',
           f'Created: {data["created_at_utc"]}',
           f'Validation-selected model: **{data["champion_validation_only"]}**',"",
           "| Target issue | "+ " | ".join(data["predictions"][0]["models"])+" |",
           "|---|"+ "|".join("---" for _ in data["predictions"][0]["models"])+"|"]
    for item in data["predictions"]:
        lines.append("| "+item["issue"]+" | "+" | ".join("".join(map(str,codes)) for codes in item["models"].values())+" |")
    lines.extend(["","These are fixed-origin research forecasts, not evidence of a predictive edge.",
                  "Do not infer next-day updates if the masked private source is unchanged."])
    latest.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("saved:",target)

if __name__=="__main__":
    main()
