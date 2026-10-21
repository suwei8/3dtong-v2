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




def _sealed_timestamp(path, issue):
    """Return public seal creation time. Never read or print model votes."""
    if not path.is_file():
        return None, False
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("target_issue") != issue:
            return None, True
        raw = record.get("generated_at_utc")
        return (parse_aware_timestamp(raw) if raw else None), False
    except (ValueError, TypeError, KeyError, UnicodeError, OSError):
        return None, True


def _first_git_commit_timestamp(repository, file_path):
    """The file's immutable Git commit time, not guaranteed remote push time.

    Only opt-in in workflow with full history; missing Git history -> unknown.
    """
    if repository is None or not file_path.is_file():
        return None
    import subprocess
    root = Path(repository).resolve()
    try:
        relative = file_path.resolve().relative_to(root)
    except ValueError:
        return None
    try:
        cmd = subprocess.run(
            ["git", "-C", str(root), "log", "--diff-filter=A",
             "--format=%cI", "--", str(relative)],
            check=True, capture_output=True, text=True, timeout=8)
        stamp = cmd.stdout.strip().splitlines()
        return parse_aware_timestamp(stamp[-1]) if stamp else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _elapsed_nonnegative(after, before, scale, ndigits=1):
    if after is None or before is None or after < before:
        return None
    return round((after-before).total_seconds()/scale, ndigits)

def audit_source(history_path, source_commit_utc, predictions_dir="predictions/live/runs",
                 evaluations_dir="reports/live", min_issue="2026274",
                 freshness_hours=36, as_of_utc=None, public_git_repo=None):
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
    next_created, next_invalid = _sealed_timestamp(frozen_next, data["target"])
    next_optional = frozen_dir.parent / "opencode-runs" / f'{data["target"]}.json'
    optional_created, optional_invalid = _sealed_timestamp(next_optional, data["target"])
    latest_created = (
        _sealed_timestamp(frozen_dir/f"{latest_frozen_issue}.json", latest_frozen_issue)[0]
        if latest_frozen_issue else None
    )
    git_sealed = _first_git_commit_timestamp(public_git_repo, frozen_next)
    # If CSV changed again after prediction, the newest source timestamp is
    # no longer comparable to the original source cutoff -> unknown, not negative.
    source_to_created = _elapsed_nonnegative(next_created, committed, 60)
    creation_to_git_commit = _elapsed_nonnegative(git_sealed, next_created, 1)
    problem_codes = []
    if age_hours < -0.25:
        problem_codes.append("SOURCE_CLOCK_IN_FUTURE")
    elif age_hours > freshness_hours:
        problem_codes.append("SOURCE_NOT_UPDATED")
    if next_invalid:
        problem_codes.append("INVALID_NEXT_FORECAST_SEAL")
    if optional_invalid:
        problem_codes.append("INVALID_OPTIONAL_FORECAST_SEAL")
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
        "latest_forecast_created_at_utc": latest_created.isoformat() if latest_created else None,
        "next_forecast_created_at_utc": next_created.isoformat() if next_created else None,
        "next_forecast_first_git_commit_at_utc": git_sealed.isoformat() if git_sealed else None,
        "next_forecast_generation_delay_from_current_source_minutes": source_to_created,
        "next_forecast_creation_to_git_commit_seconds": creation_to_git_commit,
        "next_optional_forecast_frozen": next_optional.is_file(),
        "next_optional_created_at_utc": optional_created.isoformat() if optional_created else None,
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
        f'最新封存记录生成时间（UTC）：{audit["latest_forecast_created_at_utc"] or "待记录"}',
        f'下一期传统预测生成时间（UTC）：{audit["next_forecast_created_at_utc"] or "尚未封存/未知"}',
        f'下一期传统预测首次Git提交时间（UTC）：{audit["next_forecast_first_git_commit_at_utc"] or "未知"}',
        f'当前数据源提交→下一期预测生成（分钟）：{audit["next_forecast_generation_delay_from_current_source_minutes"] if audit["next_forecast_generation_delay_from_current_source_minutes"] is not None else "无法确认"}',
        f'预测生成→Git提交（秒）：{audit["next_forecast_creation_to_git_commit_seconds"] if audit["next_forecast_creation_to_git_commit_seconds"] is not None else "无法确认"}',
        f'下一期可选OpenCode预测已封存：{"是" if audit["next_optional_forecast_frozen"] else "否"}',
        f'下一期OpenCode生成时间（UTC）：{audit["next_optional_created_at_utc"] or "尚未封存/未知"}',
        f'监测起点：{audit["monitoring_started_at_issue"]}',
        f'纳入监测的已开奖期数：{audit["completed_issues_monitored"]}',
        "",
        codes("已开奖但缺失事前预测",audit["missed_completed_forecasts"]),
        codes("已开奖且有预测，但尚未评分",audit["completed_forecasts_awaiting_score"]),
        codes("告警代码",audit["problem_codes"]),
        "",
        "当最新开奖尚未产生下一期预测时，不直接判定为漏报，因为期号并不能可靠推断开奖日期。",
        "生成时间取自公开封存记录；首次Git提交时间不等于远端实际推送完成时间。若数据源在预测后又更新，延迟统计标记未知。",
        "跳过/错误原因以GitHub Actions运行日志为准，以上告警代码只反映当前数据与封存状态。",
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
    parser.add_argument("--public-git-repo",default=None,
                        help="Optional full-history public repo for first seal commit timestamps")
    parser.add_argument("--out",default="reports")
    parser.add_argument("--freshness-hours",type=int,default=36)
    parser.add_argument("--min-issue",default="2026274")
    args=parser.parse_args()
    report=audit_source(args.history,args.source_commit_utc,
                        args.predictions,args.evaluations,args.min_issue,
                        args.freshness_hours,public_git_repo=args.public_git_repo)
    page=publish(report,args.out)
    print(f'{report["health"]}: {page}')
    for code in report["problem_codes"]:
        print("warning:",code)


if __name__=="__main__":
    main()
