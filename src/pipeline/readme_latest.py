"""Keep the README's topmost forecast view derived from genuine immutable seals.

Reads public, already-frozen model digits only, never private CSVs or winning
numbers. This display is a replaceable projection, not a new prediction seal.
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

START = "<!-- 3DTONG_LATEST_START -->"
END = "<!-- 3DTONG_LATEST_END -->"
MODEL_NAME = re.compile(r"[a-zA-Z0-9/_.-]{1,100}\Z")
ISSUE = re.compile(r"\d{7}\Z")
BEIJING = ZoneInfo("Asia/Shanghai")


def _timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("sealed time must be timezone-aware")
    return dt.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S")


def _digits(digits):
    if (not isinstance(digits, list) or len(digits) != 3 or
            any(type(d) is not int or not 0 <= d <= 9 for d in digits) or
            len(set(digits)) != 3):
        raise ValueError("not exactly three distinct digit integers")
    return "".join(str(d) for d in digits)


def latest_seal(directory):
    files = list(Path(directory).glob("*.json"))
    if not files:
        raise ValueError("no immutable forecast files are available")
    for item in files:
        if not ISSUE.fullmatch(item.stem):
            raise ValueError("invalid forecast filename")
    path = max(files, key=lambda file: int(file.stem))
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("type") != "prospective-next-issue"
            or data.get("target_issue") != path.stem
            or not ISSUE.fullmatch(str(data.get("known_through_issue", "")))
            or int(data["known_through_issue"]) >= int(path.stem)):
        raise ValueError("invalid immutable forecast record")
    _timestamp(data["generated_at_utc"])
    return data


def render_banner(seal, optional_dir="predictions/live/opencode-runs"):
    issue = seal["target_issue"]
    if not ISSUE.fullmatch(str(issue)):
        raise ValueError("invalid target issue")
    models = dict(seal.get("models", {}))
    chosen = seal.get("validation_selected_model")
    if not models or chosen not in models:
        raise ValueError("selected statistical model is not in sealed votes")
    for name, digits in models.items():
        if not MODEL_NAME.fullmatch(name):
            raise ValueError("invalid model name")
        _digits(digits)

    extra_file = Path(optional_dir) / (issue + ".json")
    extra_timestamp = None
    if extra_file.exists():
        extra = json.loads(extra_file.read_text(encoding="utf-8"))
        if (extra.get("type") != "optional-opencode-contestants-v1"
                or extra.get("target_issue") != issue
                or extra.get("known_through_issue") != seal["known_through_issue"]
                or extra.get("classical_frozen_at_utc") != seal["generated_at_utc"]):
            raise ValueError("optional record does not match the classical seal")
        extra_timestamp = _timestamp(extra["generated_at_utc"])
        if not isinstance(extra.get("models"), dict):
            raise ValueError("invalid optional models")
        for name, digits in extra["models"].items():
            if not MODEL_NAME.fullmatch(name) or name in models:
                raise ValueError("duplicate or invalid optional model")
            _digits(digits)
            models[name] = digits

    lines = [
        START,
        f"## 最新一期事前预测｜第 {issue} 期",
        "",
        f"**验证集选定模型：{chosen} → \`{_digits(models[chosen])}\`**",
        "",
        f'- **预测时已知至：** 第 {seal["known_through_issue"]} 期',
        f'- **原始封存时间（北京时间）：** {_timestamp(seal["generated_at_utc"])}',
    ]
    if extra_timestamp:
        lines.append(f"- **OpenCode 独立封存时间（北京时间）：** {extra_timestamp}")
    lines += [
        "",
        "| 模型 | 三个候选数字 |",
        "|---|---:|",
    ]
    for name, digits in models.items():
        display_name = name + ("（验证集选定）" if name == chosen else "")
        lines.append(f"| {display_name} | **{_digits(digits)}** |")
    lines += [
        "",
        f"[本期预测详情](predictions/live/history/{issue}.md) · "
        "[最新预测页面](predictions/live/LATEST.md) · "
        "[往期全部记录](predictions/live/HISTORY.md) · "
        "[实战排行榜](reports/live-leaderboard.md)",
        "",
        "说明：仅展示开奖前已封存的三个不同候选数字，不展示实际开奖号码。"
        "这不是开奖结果或中奖保证；模型尚无经过确认的预测优势。",
        END,
    ]
    return "\n".join(lines)


def update_readme(readme_path="README.md", forecasts="predictions/live/runs",
                  optional_dir="predictions/live/opencode-runs"):
    file = Path(readme_path)
    original = file.read_text(encoding="utf-8")
    banner = render_banner(latest_seal(forecasts), optional_dir)
    starts, ends = original.count(START), original.count(END)
    if (starts, ends) == (1, 1):
        before, tail = original.split(START, 1)
        _, after = tail.split(END, 1)
        revised = before + banner + after
    elif (starts, ends) == (0, 0):
        lines = original.split("\n", 1)
        if len(lines) != 2 or not lines[0].startswith("# "):
            raise ValueError("README is missing its original H1 title")
        revised = lines[0] + "\n\n" + banner + "\n" + lines[1]
    else:
        raise ValueError("README latest markers are incomplete or duplicated")
    if revised != original:
        file.write_text(revised, encoding="utf-8")
        return True
    return False


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--readme", default="README.md")
    cli.add_argument("--forecasts", default="predictions/live/runs")
    cli.add_argument("--optional-forecasts", default="predictions/live/opencode-runs")
    args = cli.parse_args()
    changed = update_readme(args.readme, args.forecasts, args.optional_forecasts)
    print("README latest forecast: " + ("updated" if changed else "already up to date"))


if __name__ == "__main__":
    main()
