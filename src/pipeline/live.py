"""One-issue immutable predictions; optional anonymous LLM votes seal separately."""
import argparse
import json
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from src.data.live import load_live_history
from src.pipeline.train import train_all


def compute_llm_budget(max_seconds, deadline_beijing=None,
                       publication_reserve_seconds=120, now=None):
    """Seconds available to call remote LLMs while reserving Git publish time.

    Beijing publication time never silently rolls to tomorrow. The scheduler
    is best-effort; a late runner must skip LLMs rather than use a past cutoff.
    """
    if max_seconds is not None and (type(max_seconds) not in (int,float)
                                     or not 0<=max_seconds<=1800):
        raise ValueError("invalid LLM budget seconds")
    if (type(publication_reserve_seconds) not in (int,float)
            or not 0<=publication_reserve_seconds<=3600):
        raise ValueError("invalid publication reserve seconds")
    if deadline_beijing is None:
        return max_seconds
    deadline=datetime.strptime(deadline_beijing,"%H:%M")
    beijing=ZoneInfo("Asia/Shanghai")
    current=now or datetime.now(beijing)
    if current.tzinfo is None:
        raise ValueError("clock must be timezone-aware")
    current=current.astimezone(beijing)
    limit=current.replace(hour=deadline.hour,minute=deadline.minute,
                          second=0,microsecond=0)
    remaining=max(0,(limit-current).total_seconds()-publication_reserve_seconds)
    return min(remaining,max_seconds) if max_seconds is not None else remaining


def freeze_live(path,out="predictions/live",source_max_age_hours=0,
                source_commit_utc=None):
    source=load_live_history(path)
    if source_max_age_hours:
        if not source_commit_utc:
            raise ValueError("source commit timestamp required")
        commit=datetime.fromisoformat(source_commit_utc.replace("Z","+00:00"))
        age=(datetime.now(timezone.utc)-commit.astimezone(timezone.utc)).total_seconds()/3600
        if age<0 or age>source_max_age_hours:
            raise ValueError(f"source CSV commit is stale or in future ({age:.1f}h)")
    dest=Path(out)
    frozen=dest/"runs"/f'{source["target"]}.json'
    if frozen.exists():
        old=json.loads(frozen.read_text(encoding="utf-8"))
        if old["target_issue"]!=source["target"]:
            raise ValueError("existing sealed target mismatch")
        print("existing sealed forecast not overwritten:",frozen)
        return False
    arena=train_all(source["history"])
    models=dict(arena["predictions"])
    from src.evaluation.control import NAME as CONTROL_NAME, control_digits
    models[CONTROL_NAME]=control_digits(source["cutoff"],source["target"])
    data={"schema":5,"type":"prospective-next-issue",
          "generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "target_issue":source["target"],"known_through_issue":source["cutoff"],
          "source_sha256":source["source_sha256"],
          "pending_source_record":source["pending_source_record"],
          "validation":arena["scores"],
          "validation_selected_model":arena["champion_validation_only"],
          "control_algorithm":"sha256-rank-v1",
          "research_protocol":"first-200-valid-prospective-issues-v1",
          "models":models,
          "notes":"Only actual successful anonymous CLI JSON responses enter optional forecasts; no model has proven an edge."}
    frozen.parent.mkdir(parents=True,exist_ok=True)
    frozen.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=["# 3dtong-v2 live forecast","",
        f'**Next target issue: {data["target_issue"]}**',
        f'Latest known completed issue: {data["known_through_issue"]}',
        f'Frozen: {data["generated_at_utc"]}',
        f'Validation-selected statistical model: {data["validation_selected_model"]}',"",
        "| Contestant | Three distinct digits |","|---|---|"]
    for name,digits in models.items():
        md.append(f'| {name} | {"".join(map(str,digits))} |')
    md.extend(["","[查看全部往期预测与命中结果](HISTORY.md)","","Frozen predictions are immutable. Optional anonymous LLM votes are sealed separately in kilo-runs and require at least three actual Kilo successes for derived votes; no model has a proven edge."])
    (dest/"LATEST.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("frozen:",frozen)
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True)
    p.add_argument("--out",default="predictions/live")
    p.add_argument("--max-source-age-hours",type=float,default=0)
    p.add_argument("--source-commit-utc")
    args=p.parse_args()
    freeze_live(args.history,args.out,args.max_source_age_hours,
                args.source_commit_utc)

if __name__=="__main__":
    main()
