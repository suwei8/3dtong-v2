"""Score only previously sealed, one-issue prospective forecasts.

Ground-truth draw values stay in the private source. Public outputs include
only hit flags and aggregates, not the private source's KaiJiang column.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from src.data.loader import load_history
from src.evaluation.metrics import hit_any_digit


def evaluate_live(locked,results):
    if locked.get("type")!="prospective-next-issue":
        raise ValueError("not a prospective prediction")
    target=locked["target_issue"]
    if int(locked["known_through_issue"]) >= int(target):
        raise ValueError("source cutoff not before forecast target")
    if target not in results:
        return None
    output={"target_issue":target,"frozen_at":locked["generated_at_utc"],
            "source_cutoff":locked["known_through_issue"],"scores":{}}
    for name,digits in locked["models"].items():
        if (len(digits)!=3 or len(set(digits))!=3
                or any(type(d) is not int or not 0<=d<=9 for d in digits)):
            raise ValueError("expected exactly three distinct digit integers")
        output["scores"][name]=bool(hit_any_digit(digits,results[target]))
    return output


def run(full_history,forecasts,output_dir):
    source={r["Issue"]:r["KaiJiang"] for r in load_history(full_history)}
    target=Path(output_dir)
    out=target/"live"
    out.mkdir(parents=True,exist_ok=True)
    totals=defaultdict(lambda:[0,0])
    completed=0
    for f in sorted(Path(forecasts).glob("*.json")):
        locked=json.loads(f.read_text(encoding="utf-8"))
        evaluation=evaluate_live(locked,source)
        if evaluation is None:
            continue
        completed+=1
        report=out/f.name
        report.write_text(json.dumps(evaluation,ensure_ascii=False,indent=2)+"\n",
                          encoding="utf-8")
        for model,hit in evaluation["scores"].items():
            totals[model][0]+=int(hit)
            totals[model][1]+=1
    lines=["# Prospective Model Arena","",
           "Only one sealed live forecast per target issue is scored.",
           "Historical masked holdout results are **excluded**.","",
           "| Model | Hits | Total | Hit rate |","|---|---:|---:|---:|"]
    for name,(hits,n) in sorted(totals.items(),key=lambda item:(-item[1][0]/item[1][1],item[0])):
        lines.append(f"| {name} | {hits} | {n} | {100*hits/n:.2f}% |")
    lines.extend(["",f"Scored target issues: {completed}.",
                  "Chance baseline for fixed three-digit set: 65.7%.",
                  "Small-sample results do not establish an edge."])
    (target/"live-leaderboard.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"scored {completed} sealed issues")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--full-history",required=True)
    p.add_argument("--forecasts",default="predictions/live/runs")
    p.add_argument("--out",default="reports")
    a=p.parse_args()
    run(a.full_history,a.forecasts,a.out)


if __name__=="__main__":
    main()
