"""Read-only monitoring of draw ingestion, pre-result coverage and delayed scoring.

Public outputs contain issue IDs and operational metadata ONLY. Complete
private draw codes, auth tokens, and the private CSV never enter this repository.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from src.data.live import load_live_history


def parse_aware_timestamp(value):
    if not value:
        raise ValueError("source commit timestamp required")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("source commit timestamp requires timezone")
    return dt.astimezone(timezone.utc)


def audit_source(history_path, source_commit_utc, predictions_dir="predictions/live/runs",
                 evaluations_dir="reports/live", min_issue="2026274",
                 freshness_hours=36, as_of_utc=None):
    """Audit only known completed issues, never invent a due-date or result."""
    now = as_of_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("current time requires timezone")
    now = now.astimezone(timezone.utc)
    committed = parse_aware_timestamp(source_commit_utc)
    age_hours = (now - committed).total_seconds() / 3600
    data = load_live_history(history_path)
    history = data["history"]
    if not min_issue.isdigit() or len(min_issue) != 7:
        raise ValueError("invalid monitoring start issue")
    if freshness_hours <= 0:
        raise ValueError("freshness threshold must be positive")

    frozen_dir = Path(predictions_dir)
    scored_dir = Path(evaluations_dir)
    missed_forecasts = []
    missed_evaluations = []
    completed_monitored = 0
    for row in history:
        issue = row["Issue"]
        if int(issue) < int(min_issue):
            continue
        completed_monitored += 1
        if not (frozen_dir / f"{issue}.json").exists():
            missed_forecasts.append(issue)
        elif not (scored_dir / f"{issue}.json").exists():
            missed_evaluations.append(issue)

    frozen_next = frozen_dir / f'{data["target"]}.json'
    latest_frozen_issue = max(
        (p.stem for p in frozen_dir.glob("*.json") if p.stem.isdigit() and len(p.stem)==7),
        default=None
    )
    problem_codes = []
    if age_hours < -0.25:
        problem_codes.append("SOURCE_CLOCK_IN_FUTURE")
    elif age_hours > freshness_hours:
        problem_codes.append("SOURCE_NOT_UPDATED")
    if missed_forecasts:
        problem_codes.append("COMPLETED_ISSUES_WITHOUT_FROZEN_FORECAST")
    if missed_evaluations:
        problem_codes.append("COMPLETED_ISSUES_NOT_SCORED")
    return {
        "schema": 1,
        "generated_at_utc": now.isoformat(),
        "health": "attention_required" if problem_codes else "ok",
        "problem_codes": problem_codes,
        "private_source": "suwei8/pinble-data/data/k3_full_history.csv",
        "private_csv_included": False,
        "source_commit_at_utc": committed.isoformat(),
        "source_age_hours": round(age_hours, 2),
        "freshness_threshold_hours": freshness_hours,
        "latest_completed_issue": history[-1]["Issue"],
        "next_issue_from_latest_result": data["target"],
        "next_issue_forecast_frozen": frozen_next.is_file(),
        "latest_frozen_issue": latest_frozen_issue,
        "completed_issues_monitored": completed_monitored,
        "missed_completed_forecasts": missed_forecasts,
        "completed_forecasts_awaiting_score": missed_evaluations,
        "monitoring_started_at_issue": min_issue,
        "note": "A missing NEXT forecast is not treated as late: the next drawing's deadline is not inferable from draw issue IDs. Only already-completed missing forecasts count as missed."
    }


def publish(audit, output_dir="reports"):
    target=Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target/"operations.json").write_text(
        json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    def codes(label, values):
        return f'{label}: ' + (", ".join(values[-20:]) if values else "none")
    lines=[
        "# 3dtong-v2 运行健康检查",
        "",
        f'**状态：{audit["health"]}**',
        f'检查时间（UTC）：{audit["generated_at_utc"]}',
        f'最新已开奖期号：**{audit["latest_completed_issue"]}**',
        f'数据源最近提交（UTC）：{audit["source_commit_at_utc"]}',
        f'源数据年龄：{audit["source_age_hours"]} 小时（阈值 {audit["freshness_threshold_hours"]} 小时）',
        f'下一目标期号：**{audit["next_issue_from_latest_result"]}**',
        f'下一期已封存预测：**{"是" if audit["next_issue_forecast_frozen"] else "否"}**',
        f'最后封存期号：{audit["latest_frozen_issue"] or "none"}',
        f'监测起点：{audit["monitoring_started_at_issue"]}',
        f'纳入监测的已开奖期数：{audit["completed_issues_monitored"]}',
        "",
        codes("已开奖但缺失事前预测",audit["missed_completed_forecasts"]),
        codes("已开奖且有预测，但尚未评分",audit["completed_forecasts_awaiting_score"]),
        codes("告警代码",audit["problem_codes"]),
        "",
        "当最新开奖尚未产生下一期预测时，不直接判定为漏报，因为期号并不能可靠推断开奖日期。",
        "此报告只包含期号和运行状态，不公开私有 CSV、开奖号码或任何凭证。",
        "不以健康检查正常证明任何模型有预测优势。"
    ]
    (target/"STATUS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return target/"STATUS.md"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--history",required=True)
    parser.add_argument("--source-commit-utc",required=True)
    parser.add_argument("--predictions",default="predictions/live/runs")
    parser.add_argument("--evaluations",default="reports/live")
    parser.add_argument("--out",default="reports")
    parser.add_argument("--freshness-hours",type=int,default=36)
    parser.add_argument("--min-issue",default="2026274")
    args=parser.parse_args()
    report=audit_source(args.history,args.source_commit_utc,
                        args.predictions,args.evaluations,args.min_issue,
                        args.freshness_hours)
    page=publish(report,args.out)
    print(f'{report["health"]}: {page}')
    for code in report["problem_codes"]:
        print("warning:",code)


if __name__=="__main__":
    main()
