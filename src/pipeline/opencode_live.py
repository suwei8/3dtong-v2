"""Optional OpenCode votes, immutable and independent of classical forecasts.

Never adds late model votes to the classical forecast. A separate git-sealed
JSON file is scored only when its original commit precedes the result.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.data.live import load_live_history
from src.pipeline.live import compute_opencode_budget,train_all

BJ=ZoneInfo("Asia/Shanghai")


def optional_preflight(history,root="predictions/live",*,now=None,source_commit_utc=None):
    source=load_live_history(history)
    dest=Path(root)
    target=source["target"]
    orig=dest/"runs"/(target+".json")
    extra=dest/"opencode-runs"/(target+".json")
    if extra.exists():
        record=json.loads(extra.read_text(encoding="utf-8"))
        if record.get("target_issue")!=target or record.get("type")!="optional-opencode-contestants-v1":
            raise ValueError("invalid existing optional immutable forecast")
        return {"issue":target,"new":False,"reason":"already_optional_frozen"}
    if not orig.exists():
        return {"issue":target,"new":False,"reason":"classical_forecast_not_ready"}
    parent=json.loads(orig.read_text(encoding="utf-8"))
    if (parent.get("target_issue")!=target or
            parent.get("known_through_issue")!=source["cutoff"] or
            parent.get("type")!="prospective-next-issue"):
        raise ValueError("classical source/target mismatch")
    if any(k.startswith("opencode/") for k in parent.get("models",{})):
        return {"issue":target,"new":False,"reason":"legacy_embedded_opencode"}
    current=now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("timezone required")
    if current.astimezone(BJ).strftime("%H:%M")>="21:10":
        return {"issue":target,"new":False,"reason":"past_beijing_cutoff"}
    if source_commit_utc:
        committed=datetime.fromisoformat(source_commit_utc.replace("Z","+00:00"))
        if committed.tzinfo is None:
            raise ValueError("timezone required for source commit")
        delta=(current.astimezone(timezone.utc)-committed.astimezone(timezone.utc)).total_seconds()
        if not -900<=delta<=86400:
            return {"issue":target,"new":False,"reason":"source_too_old"}
    return {"issue":target,"new":True,"reason":"optional_eligible"}


def freeze_optional(history,root="predictions/live",source_commit_utc=None,
                    budget_seconds=240):
    check=optional_preflight(history,root,source_commit_utc=source_commit_utc)
    if not check["new"]:
        print("no optional submission:",check["reason"])
        return False
    source=load_live_history(history)
    parent=json.loads((Path(root)/"runs"/(check["issue"]+".json")).read_text(encoding="utf-8"))
    from src.models.llm.opencode_free import compete
    from src.models.llm.vote_ensemble import combine_open_votes
    models={}
    statuses={}
    budget=compute_opencode_budget(budget_seconds,"21:10",120)
    contestants=compete(source["history"],budget_seconds=budget)
    for name,answer in contestants.items():
        statuses[name]={"status":answer["status"]}
        if answer["status"]=="ok":
            models[name]=answer["digits"]
        else:
            statuses[name]["reason"]=answer.get("reason","unavailable")
    # Compute tie-break probabilities only from the same cutoff as parent.
    if sum(x["status"]=="ok" for x in contestants.values())>=3:
        arena=train_all(source["history"])
        tie=arena["probabilities"]["ensemble"]
    else:
        tie=[.1]*10  # never used if there are under three contestants
    combined=combine_open_votes(contestants,tie)
    models.update(combined["predictions"])
    if not optional_preflight(history,root,source_commit_utc=source_commit_utc)["new"]:
        print("optional stage skipped; cut-off or parent eligibility changed")
        return False
    created=datetime.now(timezone.utc)
    parent_time=datetime.fromisoformat(parent["generated_at_utc"].replace("Z","+00:00"))
    if parent_time.tzinfo is None or created<parent_time:
        raise ValueError("optional vote cannot precede classical parent")
    result={
        "schema":1,"type":"optional-opencode-contestants-v1",
        "target_issue":source["target"],"known_through_issue":source["cutoff"],
        "generated_at_utc":created.isoformat(),
        "classical_frozen_at_utc":parent["generated_at_utc"],
        "models":models,"opencode_challengers":statuses,
        "derived_challengers":combined["statuses"],
        "notes":"Independently sealed optional votes; never edit parent ML prediction."
    }
    output=Path(root)/"opencode-runs"/(source["target"]+".json")
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        raise ValueError("optional vote was already sealed; refusal to overwrite")
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--history",required=True)
    cli.add_argument("--root",default="predictions/live")
    cli.add_argument("--source-commit-utc",required=True)
    cli.add_argument("--preflight",action="store_true")
    cli.add_argument("--github-output")
    cli.add_argument("--max-seconds",type=int,default=240)
    args=cli.parse_args()
    if args.preflight:
        check=optional_preflight(args.history,args.root,source_commit_utc=args.source_commit_utc)
        if args.github_output:
            with Path(args.github_output).open("a",encoding="utf-8") as f:
                f.write("issue="+check["issue"]+"\n")
                f.write("new="+str(check["new"]).lower()+"\n")
                f.write("reason="+check["reason"]+"\n")
        print(check)
    else:
        freeze_optional(args.history,args.root,args.source_commit_utc,args.max_seconds)


if __name__=="__main__":
    main()
