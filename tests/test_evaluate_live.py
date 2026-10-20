"""True future-only scoreboard invariants and confidence interval checks."""
import json

import pytest
from src.pipeline.evaluate_live import evaluate_live, run, wilson_interval


def forecast(issue, cutoff, status=None, votes=None):
    return {
        "type": "prospective-next-issue",
        "target_issue": issue,
        "known_through_issue": cutoff,
        "generated_at_utc": "2026-10-15T11:00:00+08:00",
        "models": votes or {"xgboost": [1,2,3]},
        "opencode_challengers": status or {}
    }


def test_wilson_bounds_and_zero_sample():
    assert wilson_interval(0,0) is None
    lo, hi=wilson_interval(9,10)
    assert 0 < lo < 0.9 < hi <= 1
    assert wilson_interval(3,3)[1] == pytest.approx(1)
    with pytest.raises(ValueError):
        wilson_interval(4,3)


def test_cannot_score_pending_or_label_prior_issue():
    pred=forecast("2026274","2026273")
    assert evaluate_live(pred, {"2026273":"123"}) is None
    assert evaluate_live(pred,{"2026274":"176"})["scores"]["xgboost"]
    pred["known_through_issue"]="2026274"
    with pytest.raises(ValueError):
        evaluate_live(pred, {"2026274":"176"})


def test_reject_invalid_output_and_naive_stamp():
    pred=forecast("2026274","2026273",votes={"fake":[3,3,3]})
    with pytest.raises(ValueError):
        evaluate_live(pred,{"2026274":"176"})
    pred=forecast("2026274","2026273")
    pred["generated_at_utc"]="2026-10-15T10:00:00"
    with pytest.raises(ValueError):
        evaluate_live(pred,{"2026274":"176"})


def test_distinct_denominators_skip_does_not_count_as_miss(tmp_path, monkeypatch):
    from src.pipeline import evaluate_live as app
    # Private loader mocked: tests never access private CSV.
    monkeypatch.setattr(app,"load_live_history",lambda _: {
        "history": [{"Issue":"2026274","KaiJiang":"908"}]})
    root=tmp_path/"predictions"
    root.mkdir()
    p=forecast("2026274","2026273",
               status={"opencode/mimo-v2.6-flash-free":{"status":"skipped","reason":"timeout"},
                       "opencode/space-bunny-free":{"status":"ok"}},
               votes={"xgboost":[0,3,4],"opencode/space-bunny-free":[1,2,3]})
    (root/"2026274.json").write_text(json.dumps(p),encoding="utf-8")
    h=run("private.csv",root,tmp_path/"reports")
    assert h["scored_issues"] == 1 and h["pending_issues"] == 0
    assert h["models"]["xgboost"]["hits"] == 1
    assert h["models"]["opencode/mimo-v2.6-flash-free"]["published"] == 0
    assert h["models"]["opencode/mimo-v2.6-flash-free"]["attempted"] == 1
    assert h["models"]["opencode/space-bunny-free"]["published"] == 1
    output=json.loads((tmp_path/"reports/live/2026274.json").read_text())
    assert "KaiJiang" not in json.dumps(output)
    leaderboard=(tmp_path/"reports/live-leaderboard.md").read_text(encoding="utf-8")
    assert "# 实战预测模型排行榜" in leaderboard
    assert "| 模型标识 | 命中次数 | 有效预测次数 | 命中率 |" in leaderboard
    assert "已评分期数：" in leaderboard
    assert "随机选择 3 个不同数字" in leaderboard
    assert "908" not in json.dumps(output)
    paired=json.loads((tmp_path/"reports/live-paired.json").read_text(encoding="utf-8"))
    assert paired["completed_source_issues"]==1
    assert paired["sealed_completed_issues"]==1
    assert paired["scored_completed_issues"]==1
    assert paired["forecast_coverage_pct"]==100
    assert paired["planned_pair_start_issue"]=="2026281"
    assert not paired["inferential_statistics_run"]
    assert "908" not in json.dumps(paired)
    assert "预测覆盖率" in (tmp_path/"reports/live-paired.md").read_text(encoding="utf-8")
    # Rerunning the same issue must not inflate counts.
    rerun=run("private.csv",root,tmp_path/"reports")
    assert rerun==h


def test_duplicate_alias_must_fail(tmp_path,monkeypatch):
    from src.pipeline import evaluate_live as app
    monkeypatch.setattr(app,"load_live_history",lambda _: {
        "history": [{"Issue":"2026274","KaiJiang":"908"}]})
    folder=tmp_path/"inputs"
    folder.mkdir()
    p=forecast("2026274","2026273")
    (folder/"2026274.json").write_text(json.dumps(p))
    (folder/"duplicate.json").write_text(json.dumps(p))
    with pytest.raises(ValueError,match="mismatched"):
        run("source.csv",folder,tmp_path/"reports")


def test_invalid_status_fails_closed(tmp_path,monkeypatch):
    from src.pipeline import evaluate_live as app
    monkeypatch.setattr(app,"load_live_history",lambda _: {
        "history": [{"Issue":"2026274","KaiJiang":"908"}]})
    folder=tmp_path/"inputs"
    folder.mkdir()
    p=forecast("2026274","2026273",
                status={"opencode/fake":{"status":"ok"}})
    (folder/"2026274.json").write_text(json.dumps(p))
    with pytest.raises(ValueError, match="requires"):
        run("source.csv",folder,tmp_path/"reports")
