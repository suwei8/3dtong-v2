"""Fast, standard-library-only, fail-closed preflight for GitHub schedules.

This runs BEFORE pip/npm installation or classical model training. Delayed
scheduled jobs must not use old completed results to backfill an already-drawn
issue. The last source CSV commit time is a freshness guard, not an independent
proof that a future draw is unknown.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone, time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo

from src.data.live import load_live_history

BEIJING = ZoneInfo("Asia/Shanghai")


def assess(history, forecasts_dir, source_commit_utc, *, now=None,
           source_max_age_hours=24, deadline_beijing="21:10"):
    source = load_live_history(history)
    issue = source["target"]
    path = Path(forecasts_dir) / f"{issue}.json"

    # A previously sealed target is a legitimate no-op, even if triggered late.
    if path.exists():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if frozen.get("target_issue") != issue or frozen.get("type") != "prospective-next-issue":
            raise ValueError("existing frozen target is invalid; not safe to overwrite")
        return {"issue": issue, "new": False, "reason": "already_frozen"}

    now_utc = (now or datetime.now(timezone.utc))
    if now_utc.tzinfo is None:
        raise ValueError("clock must be timezone-aware")
    here = now_utc.astimezone(BEIJING)
    try:
        hh, mm = map(int, deadline_beijing.split(":"))
        cutoff = clock_time(hh, mm)
    except (TypeError, ValueError):
        raise ValueError("invalid Beijing cutoff HH:MM") from None
    if here.time().replace(tzinfo=None) >= cutoff:
        return {"issue": issue, "new": False, "reason": "past_beijing_cutoff"}

    if (type(source_max_age_hours) not in (int, float)
            or not 0 < source_max_age_hours <= 36):
        raise ValueError("invalid source age limit")
    if not source_commit_utc:
        raise ValueError("private CSV last-commit time is required")
    committed = datetime.fromisoformat(source_commit_utc.replace("Z", "+00:00"))
    if committed.tzinfo is None:
        raise ValueError("private CSV source commit time must include timezone")
    age = (now_utc.astimezone(timezone.utc) -
           committed.astimezone(timezone.utc)).total_seconds() / 3600
    if age < -0.25 or age > source_max_age_hours:
        return {"issue": issue, "new": False, "reason": "stale_or_future_source"}

    return {"issue": issue, "new": True, "reason": "eligible_pre_result"}


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--history", required=True)
    cli.add_argument("--forecasts", default="predictions/live/runs")
    cli.add_argument("--source-commit-utc", required=True)
    cli.add_argument("--max-source-age-hours", type=float, default=24)
    cli.add_argument("--deadline-beijing", default="21:10")
    cli.add_argument("--github-output", required=True)
    args = cli.parse_args()

    result = assess(args.history, args.forecasts, args.source_commit_utc,
                    source_max_age_hours=args.max_source_age_hours,
                    deadline_beijing=args.deadline_beijing)
    with Path(args.github_output).open("a", encoding="utf-8") as stream:
        stream.write(f'issue={result["issue"]}\n')
        stream.write(f'new={str(result["new"]).lower()}\n')
        stream.write(f'reason={result["reason"]}\n')
    print(f'preflight: issue={result["issue"]}, new={result["new"]}, '
          f'reason={result["reason"]}')
    if result["reason"] in ("past_beijing_cutoff", "stale_or_future_source"):
        print("::warning::Safe skip: cannot verify a timely pre-result forecast.")


if __name__ == "__main__":
    main()
