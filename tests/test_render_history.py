import json
from src.pipeline.render_history import render_history


def forecast(issue, digits=None, status="ok"):
    return {
        "target_issue": issue, "known_through_issue": f"{int(issue)-1:07d}",
        "generated_at_utc": "2026-10-18T16:10:26+00:00",
        "validation_selected_model": "frequency-30",
        "models": {"frequency-30": digits or [0,8,6], "xgboost": [6,0,8]},
        "opencode_challengers": {"opencode/a": {
            "status": status, "reason": "timeout" if status == "skipped" else ""}},
        "derived_challengers": {"opencode-consensus": {"status": "skipped", "contributors": []}}
    }


def test_archive_readable_with_hit_miss_and_pending(tmp_path):
    forecasts=tmp_path/"runs"; scores=tmp_path/"scores"
    forecasts.mkdir(); scores.mkdir()
    (forecasts/"2026275.json").write_text(json.dumps(forecast("2026275")))
    (forecasts/"2026276.json").write_text(json.dumps(forecast("2026276",[1,2,3])))
    (scores/"2026275.json").write_text(json.dumps({
        "target_issue":"2026275","scores":{"frequency-30":True,"xgboost":False}}))
    out=tmp_path/"HISTORY.md"; details=tmp_path/"history"
    report=render_history(forecasts,scores,out,details)
    index=out.read_text(); first=(details/"2026275.md").read_text(); second=(details/"2026276.md").read_text()
    assert report["issues"] == ["2026275","2026276"]
    assert "[查看本期](history/2026275.md)" in index
    assert "待开奖/待评分" in index and "**086**" in first
    assert "命中" in first and "未命中" in first
    assert "**123**" in second and "待开奖/待评分" in second
    assert "未生成（有效模型不足）" in second
    assert "KaiJiang" not in index+first+second and "015" not in index+first+second


def test_missing_issue_and_unavailable_model_are_clear(tmp_path):
    forecasts=tmp_path/"runs"; scores=tmp_path/"scores"
    forecasts.mkdir(); scores.mkdir()
    (forecasts/"2026275.json").write_text(json.dumps(forecast("2026275",status="skipped")))
    (forecasts/"2026277.json").write_text(json.dumps(forecast("2026277")))
    out=tmp_path/"HISTORY.md"; details=tmp_path/"history"
    render_history(forecasts,scores,out,details)
    assert "**未找到封存记录**" in out.read_text()
    assert "2026276" in out.read_text()
    detail=(details/"2026275.md").read_text()
    assert "未调用（模型不可用）" in detail and "timeout" in detail


def test_empty_archive_is_valid(tmp_path):
    out=tmp_path/"nested"/"HISTORY.md"
    result=render_history(tmp_path/"no-runs",tmp_path/"no-scores",out,tmp_path/"details")
    assert result["issues"] == [] and "期号目录" in out.read_text()



def test_independent_optional_vote_is_visible_in_markdown_without_editing_parent(tmp_path):
    import json
    from src.pipeline.render_history import render_history
    base=tmp_path/"runs";base.mkdir()
    extras=tmp_path/"opencode-runs";extras.mkdir()
    scores=tmp_path/"scores";scores.mkdir()
    classical={
        "target_issue":"2026281","known_through_issue":"2026280",
        "generated_at_utc":"2026-10-21T10:00:00+00:00",
        "validation_selected_model":"xgboost",
        "models":{"xgboost":[0,1,2]},
    }
    (base/"2026281.json").write_text(json.dumps(classical))
    addon={
        "target_issue":"2026281","type":"optional-opencode-contestants-v1",
        "known_through_issue":"2026280",
        "classical_frozen_at_utc":"2026-10-21T10:00:00+00:00",
        "generated_at_utc":"2026-10-21T10:20:00+00:00",
        "models":{"opencode/example":[3,4,5]},
        "opencode_challengers":{"opencode/example":{"status":"ok"}},
    }
    (extras/"2026281.json").write_text(json.dumps(addon))
    (scores/"2026281.json").write_text(json.dumps({
        "target_issue":"2026281",
        "scores":{"xgboost":True,"opencode/example":False}
    }))
    original=(base/"2026281.json").read_bytes()
    render_history(base,scores,tmp_path/"HISTORY.md",tmp_path/"history",extras)
    doc=(tmp_path/"history"/"2026281.md").read_text()
    index=(tmp_path/"HISTORY.md").read_text()
    assert "**012**" in doc and "**345**" in doc
    assert "OpenCode 独立封存时间" in doc
    assert "2026281" in index and "2 | 已评分" in index
    assert original==(base/"2026281.json").read_bytes()
