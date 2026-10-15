"""Operational-status monitoring must not access or publish raw draw results."""
import json
from datetime import datetime, timedelta, timezone
from src.pipeline import health


NOW=datetime(2026,10,15,10,0,tzinfo=timezone.utc)


def fake_source(last_issue="2026273"):
    rows=[
        {"Issue":"2026273","KaiJiang":"902"},
    ]
    if last_issue=="2026274":
        rows.append({"Issue":"2026274","KaiJiang":"015"})
    return {"history": rows, "target": "2026275" if last_issue=="2026274" else "2026274"}


def test_healthy_frozen_future_issue(tmp_path,monkeypatch):
    monkeypatch.setattr(health,"load_live_history",lambda _:fake_source())
    folder=tmp_path/"runs"
    folder.mkdir()
    (folder/"2026274.json").write_text('{"target_issue":"2026274"}')
    report=health.audit_source("secret.csv",(NOW-timedelta(hours=12)).isoformat(),
                               folder,tmp_path/"scores",as_of_utc=NOW)
    assert report["health"]=="ok"
    assert report["next_issue_forecast_frozen"]
    assert report["completed_issues_monitored"]==0
    page=health.publish(report,tmp_path/"reports")
    output=page.read_text()
    assert "902" not in output and "015" not in output
    assert "KaiJiang" not in (tmp_path/"reports/operations.json").read_text()


def test_missing_completed_issue_and_score(tmp_path,monkeypatch):
    monkeypatch.setattr(health,"load_live_history",lambda _:fake_source("2026274"))
    report=health.audit_source("private.csv",NOW.isoformat(),tmp_path/"runs",
                               tmp_path/"scores",as_of_utc=NOW)
    assert report["health"]=="attention_required"
    assert report["missed_completed_forecasts"]==["2026274"]
    assert report["completed_forecasts_awaiting_score"]==[]
    (tmp_path/"runs").mkdir()
    (tmp_path/"runs/2026274.json").write_text("{}")
    report2=health.audit_source("private.csv",NOW.isoformat(),tmp_path/"runs",
                                tmp_path/"scores",as_of_utc=NOW)
    assert report2["missed_completed_forecasts"]==[]
    assert report2["completed_forecasts_awaiting_score"]==["2026274"]


def test_stale_source_caught(tmp_path,monkeypatch):
    monkeypatch.setattr(health,"load_live_history",lambda _:fake_source())
    report=health.audit_source("private.csv",(NOW-timedelta(hours=40)).isoformat(),
                               tmp_path/"runs",tmp_path/"scores",as_of_utc=NOW)
    assert "SOURCE_NOT_UPDATED" in report["problem_codes"]


def test_future_clock_caught(tmp_path,monkeypatch):
    monkeypatch.setattr(health,"load_live_history",lambda _:fake_source())
    report=health.audit_source("private.csv",(NOW+timedelta(hours=1)).isoformat(),
                               tmp_path/"runs",tmp_path/"scores",as_of_utc=NOW)
    assert "SOURCE_CLOCK_IN_FUTURE" in report["problem_codes"]


def test_no_false_missed_upcoming_forecast(tmp_path,monkeypatch):
    monkeypatch.setattr(health,"load_live_history",lambda _:fake_source())
    report=health.audit_source("private.csv",NOW.isoformat(),
                               tmp_path/"runs",tmp_path/"scores",as_of_utc=NOW)
    assert report["health"]=="ok"
    assert report["next_issue_forecast_frozen"] is False
    assert report["missed_completed_forecasts"]==[]
