"""One-issue immutable predictions; optional true anonymous OpenCode model contestants."""
import argparse
import json
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from src.data.live import load_live_history
from src.pipeline.train import train_all


def compute_opencode_budget(max_seconds, deadline_beijing=None,
                            publication_reserve_seconds=120, now=None):
    """Seconds available to call remote LLMs while reserving Git publish time.

    Beijing publication time never silently rolls to tomorrow. The scheduler
    is best-effort; a late runner must skip LLMs rather than use a past cutoff.
    """
    if max_seconds is not None and (type(max_seconds) not in (int,float)
                                     or not 0<=max_seconds<=1800):
        raise ValueError("invalid OpenCode budget seconds")
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
                source_commit_utc=None,opencode=False,opencode_models=None,
                opencode_max_seconds=None,publish_deadline_beijing=None,
                publish_reserve_seconds=120):
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
    opencode_status={}
    derived_status={}
    if opencode:
        from src.models.llm.opencode_free import compete
        from src.models.llm.vote_ensemble import combine_open_votes
        budget=compute_opencode_budget(opencode_max_seconds,
                                      publish_deadline_beijing,
                                      publish_reserve_seconds)
        candidates=compete(source["history"],models=opencode_models,
                           budget_seconds=budget)
        for model,result in candidates.items():
            opencode_status[model]={"status":result["status"]}
            if result["status"]=="ok":
                models[model]=result["digits"]
            else:
                opencode_status[model]["reason"]=result.get("reason","not available")
        derived=combine_open_votes(candidates,arena["probabilities"]["ensemble"])
        models.update(derived["predictions"])
        derived_status=derived["statuses"]
    data={"schema":5,"type":"prospective-next-issue",
          "generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "target_issue":source["target"],"known_through_issue":source["cutoff"],
          "source_sha256":source["source_sha256"],
          "pending_source_record":source["pending_source_record"],
          "validation":arena["scores"],
          "validation_selected_model":arena["champion_validation_only"],
          "opencode_challengers":opencode_status,
          "derived_challengers":derived_status,
          "control_algorithm":"sha256-rank-v1",
          "research_protocol":"first-200-valid-prospective-issues-v1",
          "models":models,
          "notes":"Only actual successful anonymous CLI JSON responses enter forecasts; no model has proven an edge."}
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
    md.extend(["","## OpenCode challenger status",""])
    if opencode_status:
        md+=["| Model | Status | Reason |","|---|---|---|"]
        for name,status in opencode_status.items():
            md.append(f'| {name} | {status["status"]} | {status.get("reason","—")} |')
    else:
        md.append("OpenCode was not enabled for this frozen issue.")
    if derived_status:
        md.extend(["","## Pre-registered derived algorithms","",
                   "| Algorithm | Status | Verified OpenCode participants |",
                   "|---|---|---|"])
        for name,info in derived_status.items():
            md.append(f'| {name} | {info["status"]} | {len(info["contributors"])} |')
    md.extend(["","[查看全部往期预测与命中结果](HISTORY.md)","","Frozen predictions are immutable. Derived votes require at least three actual OpenCode successes and have no proven edge."])
    (dest/"LATEST.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("frozen:",frozen)
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True)
    p.add_argument("--out",default="predictions/live")
    p.add_argument("--max-source-age-hours",type=float,default=0)
    p.add_argument("--source-commit-utc")
    p.add_argument("--opencode",action="store_true",help="Compete with listed anonymous OpenCode models")
    p.add_argument("--opencode-models",nargs="+",help="Optional list of free model IDs")
    p.add_argument("--opencode-max-seconds",type=int,
                   help="Total OpenCode contestant budget; remaining models skip")
    p.add_argument("--publish-deadline-beijing",
                   help="HH:MM Beijing publication deadline; applied to OpenCode model time budget")
    p.add_argument("--publish-reserve-seconds",type=int,default=120,
                   help="Leave this many seconds before publication for packaging and Git")

    args=p.parse_args()
    freeze_live(args.history,args.out,args.max_source_age_hours,
                args.source_commit_utc,opencode=args.opencode,opencode_models=args.opencode_models,
                opencode_max_seconds=args.opencode_max_seconds,
                publish_deadline_beijing=args.publish_deadline_beijing,
                publish_reserve_seconds=args.publish_reserve_seconds)

if __name__=="__main__":
    main()
