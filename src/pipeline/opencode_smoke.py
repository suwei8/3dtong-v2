"""Anonymous CLI smoke check with SYNTHETIC statistics; never touch private CSV.

This test tests real provider reachability and records actual result or skipped.
It does NOT create a pre-draw issue forecast, nor does it claim model accuracy.
"""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from src.models.llm.opencode_free import load_models,predict_model


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="opencode/mimo-v2.6-flash-free")
    p.add_argument("--out",default="reports/opencode-smoke.json")
    p.add_argument("--timeout",type=int,default=60)
    args=p.parse_args()
    available,_=load_models()
    if args.model not in available:
        raise ValueError("model not in approved candidate list")
    synthetic={
      "as_of_issue":"synthetic", "presence_counts":{
        "10":{str(i):3 for i in range(10)},
        "30":{str(i):9 for i in range(10)},
        "100":{str(i):27 for i in range(10)}},
      "missing_streak":{str(i):0 for i in range(10)}}
    result=predict_model(json.dumps(synthetic,sort_keys=True),
                         args.model,timeout=args.timeout)
    status={"tested_at_utc":datetime.now(timezone.utc).isoformat(),
            "synthetic_data_only":True,"model":args.model,
            "status":result["status"],"reason":result.get("reason")}
    if result["status"]=="ok":
        status["digits"]=result["digits"]
    path=Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("OpenCode anonymous CLI smoke:",result["status"],result.get("reason",""))
    # Negative smoke is a nonzero exit: don't silently call unreachable models ready.
    if result["status"]!="ok":
        raise SystemExit(2)


if __name__=="__main__":
    main()
