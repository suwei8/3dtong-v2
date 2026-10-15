"""Prospective, immutable one-issue forecasts. Never consume withheld future outcomes."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path

from src.data.live import load_live_history
from src.pipeline.train import train_all


def freeze_live(path,out="predictions/live",source_max_age_hours=0,source_commit_utc=None):
    source=load_live_history(path)
    if source_max_age_hours:
        if not source_commit_utc:
            raise ValueError("source commit timestamp required for freshness guard")
        commit=datetime.fromisoformat(source_commit_utc.replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-commit.astimezone(timezone.utc)).total_seconds()/3600
        if age<0 or age>source_max_age_hours:
            raise ValueError(f"source CSV last commit is stale or in future ({age:.1f}h)")
    dest=Path(out)
    frozen=dest/"runs"/f'{source["target"]}.json'
    if frozen.exists():
        item=json.loads(frozen.read_text(encoding="utf-8"))
        if item["target_issue"]!=source["target"]:
            raise ValueError("existing frozen target differs")
        print("already sealed (will not overwrite):",frozen)
        return False
    arena=train_all(source["history"])
    data={"schema":1,"type":"prospective-next-issue",
          "generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "target_issue":source["target"],"known_through_issue":source["cutoff"],
          "source_sha256":source["source_sha256"],
          "pending_source_record":source["pending_source_record"],
          "validation":arena["scores"],
          "validation_selected_model":arena["champion_validation_only"],
          "models":arena["predictions"],
          "notes":"Each model uses known, completed draw results only; performance is not guaranteed."}
    frozen.parent.mkdir(parents=True,exist_ok=True)
    frozen.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=["# 3dtong-v2 live forecast","",
        f'**Next target issue: {data["target_issue"]}**',
        f'Latest known completed issue: {data["known_through_issue"]}',
        f'Frozen: {data["generated_at_utc"]}',
        f'Validation-selected model: {data["validation_selected_model"]}',"",
        "| Contestant | Three distinct digits |","|---|---|"]
    for name,digits in data["models"].items():
        md.append(f'| {name} | {"".join(map(str,digits))} |')
    md.extend(["","This is a timestamped pre-result forecast, not a claim of statistical advantage.",
               "Frozen records are never overwritten by later history."])
    (dest/"LATEST.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("frozen:",frozen)
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True)
    p.add_argument("--out",default="predictions/live")
    p.add_argument("--max-source-age-hours",type=float,default=0)
    p.add_argument("--source-commit-utc")
    a=p.parse_args()
    freeze_live(a.history,a.out,a.max_source_age_hours,a.source_commit_utc)


if __name__=="__main__":
    main()
