"""Render immutable prospective predictions as human-readable Markdown pages."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BJ = ZoneInfo("Asia/Shanghai")


def _safe(value):
    return str(value).replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def _frozen_time(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("forecast timestamp must include a timezone")
    return stamp.astimezone(BJ).strftime("%Y-%m-%d %H:%M:%S")


def _read_records(folder, kind):
    result = {}
    path = Path(folder)
    if not path.exists():
        return result
    for file in sorted(path.glob("*.json")):
        if not re.fullmatch(r"\d{7}", file.stem):
            raise ValueError(f"unexpected {kind} file name: {file.name}")
        data = json.loads(file.read_text(encoding="utf-8"))
        issue = data.get("target_issue")
        if issue != file.stem or issue in result:
            raise ValueError(f"mismatched or duplicate {kind} issue: {file.name}")
        result[issue] = data
    return result


def _status(forecast, score, model):
    if forecast.get("opencode_challengers", {}).get(model, {}).get("status") == "skipped":
        return "未调用（模型不可用）"
    if forecast.get("derived_challengers", {}).get(model, {}).get("status") == "skipped":
        return "未生成（有效模型不足）"
    if score is None:
        return "待开奖/待评分"
    value = score.get("scores", {}).get(model)
    if value is True:
        return "命中"
    if value is False:
        return "未命中"
    return "未评分（无有效预测）"


def _detail(forecast, score):
    issue = forecast["target_issue"]
    models = forecast.get("models", {})
    rows = [
        f"# 第 {issue} 期预测记录", "",
        f"- **预测时已知到：** 第 {forecast['known_through_issue']} 期",
        f"- **封存时间（北京时间）：** {_frozen_time(forecast['generated_at_utc'])}",
        f"- **验证集选出的传统模型：** {_safe(forecast.get('validation_selected_model', '未记录'))}",
        f"- **本期状态：** {'已评分' if score is not None else '待开奖/待评分'}",
        f"- **有效预测模型数：** {len(models)}", "",
        "每个模型给出三个不同数字；“命中”表示所选三个数字中至少一个出现在开奖号中。此页面不展示实际开奖号码。", "",
        "| 模型 | 预测的三个数字 | 结果 |", "|---|---:|---|",
    ]
    for name, digits in models.items():
        if (not isinstance(digits, list) or len(digits) != 3
                or any(type(d) is not int or not 0 <= d <= 9 for d in digits)
                or len(set(digits)) != 3):
            raise ValueError(f"invalid frozen digits for {issue}/{name}")
        rows.append(f"| {_safe(name)} | **{''.join(map(str, digits))}** | {_status(forecast, score, name)} |")
    # Show failed/omitted contestants in the main table too, even though they
    # have no fabricated digit vote and are never scored as a miss.
    statuses = forecast.get("opencode_challengers", {})
    for name, item in statuses.items():
        if name not in models and item.get("status") == "skipped":
            rows.append(f"| {_safe(name)} | — | 未调用（模型不可用） |")
    derived = forecast.get("derived_challengers", {})
    for name, item in derived.items():
        if name not in models and item.get("status") == "skipped":
            rows.append(f"| {_safe(name)} | — | 未生成（有效模型不足） |")
    if statuses:
        rows.extend(["", "## OpenCode 模型调用情况", "",
                     "| 模型 | 状态 | 说明 |", "|---|---|---|"])
        for name, item in statuses.items():
            status = "成功" if item.get("status") == "ok" else "跳过"
            rows.append(f"| {_safe(name)} | {status} | {_safe(item.get('reason', '—'))} |")
    derived = forecast.get("derived_challengers", {})
    if derived:
        rows.extend(["", "## 派生集成方案", "",
                     "| 算法 | 状态 | 实际参与模型数 |", "|---|---|---:|"])
        for name, item in derived.items():
            status = "成功" if item.get("status") == "ok" else "跳过"
            rows.append(f"| {_safe(name)} | {status} | {len(item.get('contributors', []))} |")
    rows.extend(["", "## 相关页面", "",
                 "- [返回往期预测总目录](../HISTORY.md)",
                 "- [实战命中率排行榜](../../../reports/live-leaderboard.md)", "",
                 "说明：模型调用失败不算预测未命中；未评分的期号不会提前计入命中率。", ""])
    return "\n".join(rows)


def render_history(forecasts_dir, scores_dir, out, details_dir):
    forecasts = _read_records(forecasts_dir, "forecast")
    scores = _read_records(scores_dir, "score")
    detail_path = Path(details_dir)
    detail_path.mkdir(parents=True, exist_ok=True)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    issues = sorted(forecasts, key=int)
    detail_files = set()
    for issue in issues:
        file = detail_path / f"{issue}.md"
        file.write_text(_detail(forecasts[issue], scores.get(issue)), encoding="utf-8")
        detail_files.add(file.name)
    for file in detail_path.glob("*.md"):
        if re.fullmatch(r"\d{7}\.md", file.name) and file.name not in detail_files:
            file.unlink()
    rows = [
        "# 往期预测记录（可直接阅读）", "",
        "这里是逐期预测的 Markdown 版本，不必打开 JSON。点击期号可查看当期所有模型号码与命中结果。", "",
        "- [最新一期预测](LATEST.md)",
        "- [实战命中率排行榜](../../reports/live-leaderboard.md)",
        "- [统计研究报告](../../reports/research.md)", "",
        "## 期号目录", "",
        "| 期号 | 预测时已知到 | 封存时间（北京时间） | 传统模型推荐 | 模型数 | 评分状态 | 详情 |",
        "|---|---|---|---:|---:|---|---|",
    ]
    previous = None
    for issue in issues:
        forecast = forecasts[issue]
        if previous is not None:
            for missing in range(int(previous) + 1, int(issue)):
                rows.append(f"| {missing:07d} | — | — | — | — | **未找到封存记录** | — |")
        champion = forecast.get("validation_selected_model")
        digits = forecast.get("models", {}).get(champion, [])
        champ_digits = "".join(map(str, digits)) if digits else "—"
        state = "已评分" if issue in scores else "待开奖/待评分"
        rows.append(
            f'| {issue} | {forecast.get("known_through_issue", "—")} | '
            f'{_frozen_time(forecast["generated_at_utc"])} | '
            f'{_safe(champion or "—")}：**{champ_digits}** | '
            f'{len(forecast.get("models", {}))} | {state} | '
            f'[查看本期](history/{issue}.md) |'
        )
        previous = issue
    rows.extend(["", "## 使用说明", "",
        "- “传统模型推荐”是该期在验证集上选出的模型号码，不等于已经证明最优。",
        "- “命中”表示三个候选数字中至少一个与开奖号码有重合，不代表顺序或完整号码命中。",
        "- “未找到封存记录”表示当前仓库没有该期的事前预测文件；不要用事后回测补成事前预测。",
        "- OpenCode 超时/不可用单独显示，不按未命中计算。", ""])
    out_path.write_text("\n".join(rows), encoding="utf-8")
    return {"issues": issues, "scored": sum(i in scores for i in issues),
            "missing_gaps": max(0, len(issues) and int(issues[-1])-int(issues[0])+1-len(issues)),
            "out": str(out_path), "detail_count": len(detail_files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", default="predictions/live/runs")
    parser.add_argument("--scores", default="reports/live")
    parser.add_argument("--out", default="predictions/live/HISTORY.md")
    parser.add_argument("--details-dir", default="predictions/live/history")
    args = parser.parse_args()
    result = render_history(args.forecasts, args.scores, args.out, args.details_dir)
    print(f"rendered {len(result['issues'])} forecasts, {result['scored']} scored; index={result['out']}")


if __name__ == "__main__":
    main()
