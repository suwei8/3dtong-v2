"""Prospective availability and same-issue matched reporting.

Works ONLY with issue IDs and already-scored boolean hit flags, never with
actual three-digit outcomes. It cannot manufacture votes for missed forecasts,
nor compute interim significance. Existing pre-registered 17-arm protocol is
independent and unchanged.
"""
import json
import re
from pathlib import Path

DEFAULT_PROTOCOL = Path(__file__).resolve().parents[2] / "configs" / "live_pair_protocol.json"


def _issue(value):
    return isinstance(value,str) and re.fullmatch(r"[0-9]{7}",value) is not None


def load_protocol(path=DEFAULT_PROTOCOL):
    protocol=json.loads(Path(path).read_text(encoding="utf-8"))
    if protocol.get("schema")!=1 or not _issue(protocol.get("start_issue")):
        raise ValueError("invalid prospective paired protocol")
    if type(protocol.get("paired_target")) is not int or protocol["paired_target"]<1:
        raise ValueError("invalid paired sample count")
    pairs=protocol.get("comparisons")
    if (not isinstance(pairs,list) or not pairs or
            any(not isinstance(p,dict) or
                not isinstance(p.get("candidate"),str) or not p["candidate"] or
                not isinstance(p.get("baseline"),str) or not p["baseline"] or
                p["candidate"]==p["baseline"] for p in pairs)):
        raise ValueError("invalid model pairs")
    if len({(p["candidate"],p["baseline"]) for p in pairs})!=len(pairs):
        raise ValueError("duplicated pair")
    return protocol


def audit(completed_issues, sealed_issues, scored_records, protocol=None,
          coverage_start="2026274"):
    """Only include issues KNOWN completed; pending forecasts are not misses.

    A model absence on a completed, sealed issue means zero joint coverage,
    never a failed prediction. First 200 joint observations per pair are
    recorded once by issue order; all displayed results are descriptive.
    """
    plan=protocol or load_protocol()
    if not _issue(coverage_start):
        raise ValueError("invalid coverage starting issue")
    issues=list(completed_issues)
    seals=list(sealed_issues)
    if (any(not _issue(i) for i in issues+seals) or
        len(set(issues))!=len(issues) or len(set(seals))!=len(seals)):
        raise ValueError("duplicate or invalid issue")
    if any(int(a)>=int(b) for a,b in zip(issues,issues[1:])):
        raise ValueError("completed issues must be chronological")
    seen=set(seals)
    scored={}
    for item in scored_records:
        target=item.get("target_issue")
        if not _issue(target) or target in scored or target not in seen:
            raise ValueError("invalid, duplicate, or nonsealed scored issue")
        votes=item.get("scores")
        if (not isinstance(votes,dict) or
                any(not isinstance(name,str) or not name or type(hit) is not bool
                    for name,hit in votes.items())):
            raise ValueError("only boolean scored predictions are allowed")
        scored[target]=votes
    completed=[issue for issue in issues if issue>=coverage_start]
    completed_set=set(completed)
    if any(i not in completed_set for i in scored):
        # Scoring an older issue outside the monitoring period is permitted.
        # Scoring a target that is not yet completed is not.
        if any(i not in issues for i in scored):
            raise ValueError("cannot score an issue absent from completed source")
    missing=[i for i in completed if i not in seen]
    awaiting=[i for i in completed if i in seen and i not in scored]
    frozen=[i for i in completed if i in seen]
    evaluated=[i for i in completed if i in scored]
    scope=[i for i in issues if i>=plan["start_issue"] and i in scored]
    comparisons={}
    for pair in plan["comparisons"]:
        a,b=pair["candidate"],pair["baseline"]
        both=[i for i in scope if a in scored[i] and b in scored[i]]
        sampled=both[:plan["paired_target"]]
        c_only=sum(scored[i][a] and not scored[i][b] for i in sampled)
        b_only=sum(scored[i][b] and not scored[i][a] for i in sampled)
        both_hit=sum(scored[i][a] and scored[i][b] for i in sampled)
        both_miss=len(sampled)-c_only-b_only-both_hit
        comparisons[f"{a}__vs__{b}"]={
            "candidate":a,"baseline":b,
            "shared_scored_issues":len(sampled),
            "target_shared_issues":plan["paired_target"],
            "joint_coverage_issues":len(both),
            "candidate_only_hits":c_only,"baseline_only_hits":b_only,
            "both_hit":both_hit,"both_miss":both_miss,
            "hit_rate_difference_pp":round(100*(c_only-b_only)/len(sampled),2)
                                      if sampled else None,
            "confirmatory_p_value":None,
            "status":"descriptive_only" if len(sampled)<plan["paired_target"] else "fixed_window_full_descriptive",
        }
    return {
        "schema":1,
        "kind":"prospective-joint-coverage-descriptive",
        "coverage_start_issue":coverage_start,
        "completed_source_issues":len(completed),
        "sealed_completed_issues":len(frozen),
        "scored_completed_issues":len(evaluated),
        "missed_completed_issues":missing,
        "sealed_but_unscored_issues":awaiting,
        "forecast_coverage_pct":round(100*len(frozen)/len(completed),2) if completed else None,
        "scoring_coverage_pct":round(100*len(evaluated)/len(completed),2) if completed else None,
        "planned_pair_start_issue":plan["start_issue"],
        "paired_target":plan["paired_target"],
        "pairs":comparisons,
        "private_draws_or_digits_included":False,
        "inferential_statistics_run":False,
        "warning":"Exploratory pair selection; do not claim model superiority from partial windows. The 17-model preregistration study remains separate.",
    }


def publish(report,out_dir="reports"):
    folder=Path(out_dir)
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"live-paired.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    def frac(n,d):
        return f"{n}/{d}" if d else "—"
    lines=[
        "# 实战事前预测：覆盖率与同期开奖配对比较","",
        "只计入**已经开奖**的期号；尚未开奖的下一期预测不算漏报。",
        "缺失事前封存文件算一次系统覆盖失败，不允许事后补成预测。",
        "真实开奖号码和预测的三个数字不会出现在此报告中。","",
        "## 预测覆盖率","",
        f'监测期号从 **{report["coverage_start_issue"]}** 开始。',
        f'已开奖期数：**{report["completed_source_issues"]}**；其中有事前封存：**{report["sealed_completed_issues"]}**；已评分：**{report["scored_completed_issues"]}**。',
        f'预测覆盖率：**{frac(report["sealed_completed_issues"],report["completed_source_issues"])}**'
        + (f'（{report["forecast_coverage_pct"]:.2f}%）' if report["forecast_coverage_pct"] is not None else ""),
        f'评分覆盖率：**{frac(report["scored_completed_issues"],report["completed_source_issues"])}**'
        + (f'（{report["scoring_coverage_pct"]:.2f}%）' if report["scoring_coverage_pct"] is not None else ""),
        '漏做事前预测：'+("、".join(report["missed_completed_issues"]) if report["missed_completed_issues"] else "无"),
        '已有事前预测但尚未评分：'+("、".join(report["sealed_but_unscored_issues"]) if report["sealed_but_unscored_issues"] else "无"),
        "",
        "## 同一期模型直接比较（仅描述，不做提前显著性检验）","",
        f'方案从 **{report["planned_pair_start_issue"]}** 开始，每组最多累计最早的 **{report["paired_target"]}** 次双方都有合法预测且已开奖的期号。',
        "模型超时/跳过/没有出现在封存记录中时，本期不进入该模型对的分母。",
        "",
        "| 模型 A | 模型 B | 同期样本进度 | 仅 A 命中 | 仅 B 命中 | 都命中 | 都未命中 | A－B命中率差 |",
        "|---|---|---:|---:|---:|---:|---:|---:|"
    ]
    for row in report["pairs"].values():
        rate="—" if row["hit_rate_difference_pp"] is None else f'{row["hit_rate_difference_pp"]:+.2f}百分点'
        lines.append(f'| {row["candidate"]} | {row["baseline"]} | '
                     f'{row["shared_scored_issues"]}/{row["target_shared_issues"]} | '
                     f'{row["candidate_only_hits"]} | {row["baseline_only_hits"]} | '
                     f'{row["both_hit"]} | {row["both_miss"]} | {rate} |')
    lines+=["",
            "**重要：** 配对是在此前探索研究之后选定的，即使达到200次，也不能仅凭这张表视为确认性证据。",
            "本报告不会计算中途 p 值，不替代原有17模型的200期预注册研究，也不会自动调整生产模型。",
            ""]
    (folder/"live-paired.md").write_text("\n".join(lines),encoding="utf-8")
    return report
