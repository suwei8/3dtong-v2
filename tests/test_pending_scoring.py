"""Regression: the upstream collector may insert next ShiJiHao before KaiJiang."""
import csv
import json

from src.pipeline.evaluate_live import run


def fake_private_csv(path, latest_code=None):
    rows=[]
    for year in (2023,2024,2025):
        days=366 if year==2024 else 365
        rows.extend({"Issue":f"{year}{n:03d}","KaiJiang":f"{(n+year)%1000:03d}"}
                    for n in range(1,days+1))
    rows.extend({"Issue":f"2026{n:03d}","KaiJiang":f"{n%1000:03d}"}
                for n in range(1,274))
    # Next issue's test record exists but has NO draw code yet.
    rows.append({"Issue":"2026274","KaiJiang":latest_code or ""})
    if latest_code:
        rows.append({"Issue":"2026275","KaiJiang":""})
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["Issue","KaiJiang"])
        writer.writeheader()
        writer.writerows(rows)


def test_pending_latest_draw_does_not_abort_scoring(tmp_path):
    source=tmp_path/"private.csv"
    fake_private_csv(source)
    predictions=tmp_path/"predictions"
    predictions.mkdir()
    prediction={
        "type":"prospective-next-issue","target_issue":"2026274",
        "known_through_issue":"2026273",
        "generated_at_utc":"2026-10-15T03:56:18+00:00",
        "models":{"traditional":[0,1,2]},
        "opencode_challengers":{"opencode/mimo-v2.6-flash-free":{
            "status":"skipped","reason":"free quota"}}
    }
    (predictions/"2026274.json").write_text(json.dumps(prediction),encoding="utf-8")
    reports=tmp_path/"reports"
    pending=run(source,predictions,reports)
    assert pending["scored_issues"]==0
    assert pending["pending_issues"]==1
    assert not (reports/"live/2026274.json").exists()

    fake_private_csv(source,latest_code="015")
    scored=run(source,predictions,reports)
    assert scored["scored_issues"]==1 and scored["pending_issues"]==0
    assert scored["models"]["traditional"]["hits"]==1
    assert scored["models"]["opencode/mimo-v2.6-flash-free"]["published"]==0
    public=(reports/"live/2026274.json").read_text(encoding="utf-8")
    assert "015" not in public and "KaiJiang" not in public
    assert run(source,predictions,reports)==scored


def test_pending_source_does_not_create_a_false_future_label(tmp_path):
    source=tmp_path/"private.csv"
    fake_private_csv(source)
    forecasts=tmp_path/"forecasts"
    forecasts.mkdir()
    status=run(source,forecasts,tmp_path/"reports")
    assert status["frozen_issues"]==0 and status["scored_issues"]==0
