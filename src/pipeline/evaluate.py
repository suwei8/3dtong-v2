"""Score frozen predictions against the separate full private result source.

This job runs AFTER a sealed prediction file has been committed. Never copy
private history rows into the public prediction repository.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from src.data.loader import load_history
from src.evaluation.metrics import hit_any_digit,hit_count

def evaluate(prediction,actuals):
    if not prediction.get("predictions") or not prediction.get("last_known_issue"):
        raise ValueError("invalid frozen prediction")
    known=int(prediction["last_known_issue"])
    report=[]
    for entry in prediction["predictions"]:
        issue=entry["issue"]
        if int(issue)<=known:
            raise ValueError("non-forward issue in prediction")
        if issue not in actuals:
            continue
        result=actuals[issue]
        for name,digits in entry["models"].items():
            if len(digits)!=3 or len(set(digits))!=3 or not all(isinstance(d,int) and 0<=d<=9 for d in digits):
                raise ValueError("model did not produce three distinct digits")
            report.append({"issue":issue,"model":name,"digits":digits,
                           "hit":hit_any_digit(digits,result),
                           "distinct_hit_count":hit_count(digits,result)})
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--full-history",required=True)
    p.add_argument("--predictions",default="predictions/runs")
    p.add_argument("--reports",default="reports")
    a=p.parse_args()
    full={r["Issue"]:r["KaiJiang"] for r in load_history(a.full_history)}
    folder=Path(a.reports)/"evaluations"
    folder.mkdir(parents=True,exist_ok=True)
    totals=defaultdict(lambda:[0,0])
    files=sorted(Path(a.predictions).glob("*.json"))
    for file in files:
        frozen=json.loads(file.read_text(encoding="utf-8"))
        measured=evaluate(frozen,full)
        output=folder/file.name
        report={"source_cutoff":frozen["last_known_issue"],"status":"retrospective_masked_holdout"
                if any(int(item["issue"]) <= int(frozen["predictions"][-1]["issue"]) for item in measured)
                else "pending","entries":measured}
        content=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
        if not output.exists() or output.read_text(encoding="utf-8")!=content:
            output.write_text(content,encoding="utf-8")
        for entry in measured:
            v=totals[entry["model"]]
            v[0]+=int(entry["hit"])
            v[1]+=1
    table=["# Model Arena leaderboard","","Forecast source: private truncated history; scoring source: private full history.",
           "These are masked historical holdouts, not prospective live results.","",
           "| Model | Hits | Evaluated | Hit rate |","|---|---:|---:|---:|"]
    for name,(hits,n) in sorted(totals.items(),key=lambda kv:(-kv[1][0]/kv[1][1],kv[0])):
        table.append(f"| {name} | {hits} | {n} | {100*hits/n:.2f}% |")
    table.extend(["","The independent theoretical Top3 hit probability is 65.7%."])
    path=Path(a.reports)/"leaderboard.md"
    path.write_text("\n".join(table)+"\n",encoding="utf-8")
    print(f"evaluated {len(files)} frozen files; {len(totals)} models")

if __name__=="__main__":
    main()
