"""Prospective-only live scoring, with duplicate protection and uncertainty bands.

The complete draw code never leaves the private data checkout. An attempted
but invalid model response cannot be presented as a miss or a scored vote.
"""
import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.data.live import load_live_history
from src.evaluation.metrics import hit_any_digit


def wilson_interval(hits, n, z=1.96):
    """Approximate two-sided 95% binomial Wilson confidence interval."""
    if not isinstance(n, int) or not isinstance(hits, int) or n < 0 or hits < 0 or hits > n:
        raise ValueError("invalid hit counts")
    if n == 0:
        return None
    p = hits / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    radius = z*math.sqrt((p*(1-p)+z*z/(4*n))/n) / denom
    return max(0.0, center-radius), min(1.0, center+radius)


def _valid_digits(digits):
    return (isinstance(digits, list) and len(digits) == 3
            and all(type(d) is int and 0 <= d <= 9 for d in digits)
            and len(set(digits)) == 3)


def evaluate_live(locked, results):
    """Return None when target has not drawn; never pull future labels."""
    if locked.get("type") != "prospective-next-issue":
        raise ValueError("not a prospective next-issue forecast")
    target = locked.get("target_issue")
    origin = locked.get("known_through_issue")
    if not isinstance(target, str) or not re.fullmatch(r"\d{7}", target):
        raise ValueError("invalid target issue")
    if not isinstance(origin, str) or not re.fullmatch(r"\d{7}", origin):
        raise ValueError("invalid origin issue")
    if int(origin) >= int(target):
        raise ValueError("source cutoff not before forecast target")
    timestamp = datetime.fromisoformat(locked["generated_at_utc"].replace("Z","+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("forecast must have timezone-aware frozen time")
    if target not in results:
        return None

    codes = locked.get("models")
    if not isinstance(codes, dict) or not codes:
        raise ValueError("no valid model forecasts")
    scores = {}
    for name, digits in codes.items():
        if not isinstance(name, str) or not name or not _valid_digits(digits):
            raise ValueError("expected exactly three distinct digit integers")
        scores[name] = bool(hit_any_digit(digits, results[target]))
    return {"target_issue": target, "frozen_at": timestamp.astimezone(timezone.utc).isoformat(),
            "source_cutoff": origin, "scores": scores}


def run(full_history, forecasts, output_dir, optional_forecasts=None):
    results = {item["Issue"]: item["KaiJiang"] for item in load_live_history(full_history)["history"]}
    output = Path(output_dir)
    evaluations = output / "live"
    evaluations.mkdir(parents=True, exist_ok=True)

    counters = defaultdict(lambda: {"hits": 0, "published": 0, "attempted": 0, "unavailable": 0})
    seen = set()
    scored_records = []
    scored_issues = 0
    pending_issues = 0
    frozen_files = sorted(Path(forecasts).glob("*.json"))
    optional_dir = (Path(optional_forecasts) if optional_forecasts is not None
                    else Path(forecasts).parent/"opencode-runs")
    optional = {}
    for file in optional_dir.glob("*.json"):
        if not re.fullmatch(r"\d{7}",file.stem) or file.stem in optional:
            raise ValueError("invalid optional contestant filename")
        record=json.loads(file.read_text(encoding="utf-8"))
        if (record.get("target_issue")!=file.stem or
            record.get("type")!="optional-opencode-contestants-v1"):
            raise ValueError("invalid optional contestant record")
        optional[file.stem]=record
    for file in frozen_files:
        data = json.loads(file.read_text(encoding="utf-8"))
        target = data.get("target_issue")
        # The file name is part of the immutable issue ID; no ambiguous aliases.
        if target != file.stem or target in seen:
            raise ValueError(f"duplicate or mismatched target file: {file.name}")
        seen.add(target)
        current = evaluate_live(data, results)
        if current is None:
            pending_issues += 1
            continue
        # Merge independent, separately Git-sealed optional votes only into the
        # derived SCORE, never the immutable original classical forecast.
        extra = optional.get(target)
        if extra is not None:
            if (extra.get("known_through_issue") != data.get("known_through_issue")
                    or extra.get("classical_frozen_at_utc") != data.get("generated_at_utc")):
                raise ValueError("optional record does not match sealed classical cutoff")
            original_time=datetime.fromisoformat(data["generated_at_utc"].replace("Z","+00:00"))
            extra_time=datetime.fromisoformat(extra["generated_at_utc"].replace("Z","+00:00"))
            if (original_time.tzinfo is None or extra_time.tzinfo is None
                    or extra_time < original_time):
                raise ValueError("optional votes cannot precede classical seal")
            votes=extra.get("models")
            if not isinstance(votes,dict):
                raise ValueError("optional model votes must be a mapping")
            for name,digits in votes.items():
                if (not isinstance(name,str) or name in current["scores"]
                        or not _valid_digits(digits)):
                    raise ValueError("invalid or duplicate optional model vote")
                current["scores"][name]=bool(hit_any_digit(digits,results[target]))
        scored_issues += 1
        scored_records.append(current)
        out = evaluations / file.name
        serialised = json.dumps(current, ensure_ascii=False, indent=2)+"\n"
        if not out.exists() or out.read_text(encoding="utf-8") != serialised:
            out.write_text(serialised, encoding="utf-8")
        # All already-published scores count exactly once per issue.
        for model, hit in current["scores"].items():
            entry = counters[model]
            entry["hits"] += int(hit)
            entry["published"] += 1
            entry["attempted"] += 1
        # Unavailable OpenCode contestants are tracked as coverage failures,
        # NOT as scored misses.
        recorded_statuses = set()
        # OpenCode raw votes and pre-registered derived votes have separate
        # availability denominators but share identical hit/miss scoring.
        for status_source in (data, extra) if extra is not None else (data,):
            for category in ("opencode_challengers", "derived_challengers"):
                challengers = status_source.get(category, {})
                if not isinstance(challengers, dict):
                    raise ValueError("invalid contestant statuses")
                for model, result in challengers.items():
                    if (not isinstance(model,str) or not model or
                            model in recorded_statuses or not isinstance(result,dict) or
                            result.get("status") not in ("ok","skipped")):
                        raise ValueError("invalid or duplicate contestant status")
                    recorded_statuses.add(model)
                    if result["status"] == "skipped":
                        if model in current["scores"]:
                            raise ValueError("skipped challenger must not have a vote")
                        counters[model]["attempted"] += 1
                        counters[model]["unavailable"] += 1
                    elif model not in current["scores"]:
                        raise ValueError("successful challenger requires a frozen vote")

    if set(optional)-seen:
        raise ValueError("optional contestant file has no original classical seal")

    # Never retain obsolete per-issue score files when input set changes.
    for file in evaluations.glob("*.json"):
        if file.stem not in seen:
            raise ValueError(f"orphan evaluation file: {file.name}")

    lines = [
        "# 实战预测模型排行榜（仅统计事前预测）",
        "",
        "每个目标期号只统计一份开奖前封存、不可覆盖的预测。",
        "历史遮蔽回测不计入以下任何实战统计。",
        "OpenCode 模型调用失败或跳过不算预测未命中。",
        "",
        "| 模型标识 | 命中次数 | 有效预测次数 | 命中率 | 95% Wilson 置信区间 | 调用次数 | 不可用次数 |",
        "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for name, row in sorted(counters.items(),
                            key=lambda item:(-item[1]["hits"]/max(1,item[1]["published"]),-item[1]["published"],item[0])):
        hits, n = row["hits"], row["published"]
        ci = wilson_interval(hits, n)
        rate = f"{hits/n*100:.2f}%" if n else "—"
        band = f"{ci[0]*100:.1f}%–{ci[1]*100:.1f}%" if ci else "—"
        lines.append(f'| {name} | {hits} | {n} | {rate} | {band} | '
                     f'{row["attempted"]} | {row["unavailable"]} |')
    lines.extend([
        "",
        f"已评分期数：**{scored_issues}**。",
        f"待开奖或待评分期数：**{pending_issues}**。",
        "",
        "随机选择 3 个不同数字、至少命中开奖号中 1 个数字的理论基准：**65.7%**（假设开奖数字独立且均匀分布）。",
        "不同模型的有效预测次数可能不同，尤其在样本很少时，不应直接把命中率排名视为模型优劣结论。",
        "置信区间反映小样本带来的不确定性，不能单独证明模型有预测优势。"
    ])
    output.mkdir(parents=True,exist_ok=True)
    (output/"live-leaderboard.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    health = {
        "schema": 1, "scored_issues": scored_issues,
        "pending_issues": pending_issues, "frozen_issues": len(frozen_files),
        "models": dict(counters), "random_baseline": 0.657
    }
    (output/"live-metrics.json").write_text(
        json.dumps(health,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    from src.evaluation.research import publish_research
    publish_research(scored_records,output)
    from src.evaluation.prospective_compare import audit, load_protocol, publish as publish_pairs
    completed_issues=[issue for issue in results]
    publish_pairs(audit(completed_issues,seen,scored_records),output)
    # New registered study starts at 2026284: do not backfill earlier known results.
    llm_protocol=Path(__file__).resolve().parents[2]/"configs"/"llm_vs_ml_pair_protocol.json"
    llm_plan=load_protocol(llm_protocol)
    llm_report=audit(completed_issues,seen,scored_records,protocol=llm_plan)
    publish_pairs(llm_report,output,file_stem="llm-vs-ml-paired",
                  title="大模型 vs LightGBM：同期开奖事前配对验证")
    print(f"scored {scored_issues} issues; {pending_issues} awaiting verified results")
    return health


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--full-history",required=True)
    parser.add_argument("--forecasts",default="predictions/live/runs")
    parser.add_argument("--optional-forecasts",default="predictions/live/opencode-runs")
    parser.add_argument("--out",default="reports")
    args=parser.parse_args()
    run(args.full_history,args.forecasts,args.out,args.optional_forecasts)


if __name__=="__main__":
    main()
