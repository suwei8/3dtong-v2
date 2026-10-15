"""One-issue frozen forecast, optional validated Cline CLI challenger."""
import argparse
import json
import os
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from src.data.live import load_live_history
from src.pipeline.train import train_all

def freeze_live(path,out="predictions/live",source_max_age_hours=0,
                source_commit_utc=None,cline=False,cline_executable="cline"):
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
    llm_info={"status":"not-configured"}
    if cline:
        from src.models.llm.contestant import summary_for_llm
        from src.models.llm.cline_mimo import ClineMimoPredictor,DEFAULT_MODEL
        agent=ClineMimoPredictor(os.environ.get("CLINE_MODEL_ID",DEFAULT_MODEL))
        with tempfile.TemporaryDirectory(prefix="3dtong-cline-") as workdir:
            answer=agent.predict(summary_for_llm(source["history"]),
                                 cwd=workdir,executable=cline_executable)
        llm_info={k:v for k,v in answer.items() if k!="digits"}
        if answer["status"]=="ok":
            models[agent.name]=answer["digits"]
    data={"schema":2,"type":"prospective-next-issue",
          "generated_at_utc":datetime.now(timezone.utc).isoformat(),
          "target_issue":source["target"],"known_through_issue":source["cutoff"],
          "source_sha256":source["source_sha256"],
          "pending_source_record":source["pending_source_record"],
          "validation":arena["scores"],
          "validation_selected_model":arena["champion_validation_only"],
          "llm_contestant":llm_info,
          "models":models,
          "notes":"Only validated real CLI output can enter forecasts."}
    frozen.parent.mkdir(parents=True,exist_ok=True)
    frozen.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=["# 3dtong-v2 live forecast","",
        f'**Next target issue: {data["target_issue"]}**',
        f'Latest known completed issue: {data["known_through_issue"]}',
        f'Frozen: {data["generated_at_utc"]}',
        f'Validation-selected model: {data["validation_selected_model"]}',
        f'Cline: {data["llm_contestant"]["status"]}',"",
        "| Contestant | Three distinct digits |","|---|---|"]
    for name,digits in data["models"].items():
        md.append(f'| {name} | {"".join(map(str,digits))} |')
    md.extend(["","Frozen predictions are immutable; models have no proven advantage."])
    (dest/"LATEST.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("frozen:",frozen)
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True)
    p.add_argument("--out",default="predictions/live")
    p.add_argument("--max-source-age-hours",type=float,default=0)
    p.add_argument("--source-commit-utc")
    p.add_argument("--cline",action="store_true")
    args=p.parse_args()
    freeze_live(args.history,args.out,args.max_source_age_hours,
                args.source_commit_utc,cline=args.cline)

if __name__=="__main__":
    main()
