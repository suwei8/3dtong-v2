"""Preflight safety and early no-op behavior, using synthetic CSV fixtures."""
import csv
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.pipeline.preflight import assess

BJ=ZoneInfo("Asia/Shanghai")


def write_history(tmp_path):
    file=tmp_path/"history.csv"
    with file.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["Issue","KaiJiang"])
        writer.writeheader()
        for year, count in ((2022,365),(2023,365),(2024,366),(2025,365)):
            for seq in range(1,count+1):
                writer.writerow({"Issue":f"{year}{seq:03d}",
                                 "KaiJiang":f"{(seq+year)%1000:03d}"})
        for seq in range(1,280):
            writer.writerow({"Issue":f"2026{seq:03d}",
                             "KaiJiang":f"{seq%1000:03d}"})
    return file


def at(hour,minute,day=21):
    return datetime(2026,10,day,hour,minute,tzinfo=BJ)


def run(file,folder,now,source_time=None):
    source_time=source_time or (now-timedelta(hours=6))
    return assess(file,folder,source_time.isoformat(),now=now)


def test_overnight_preforecast_and_daytime_checks_work(tmp_path):
    history=write_history(tmp_path)
    for hour,minute in ((0,30),(6,20),(12,20),(17,20),(19,50),(20,40)):
        now=at(hour,minute)
        result=run(history,tmp_path/"forecasts",now)
        assert result=={"issue":"2026280","new":True,"reason":"eligible_pre_result"}


def test_after_cutoff_skips_instead_of_failing(tmp_path):
    history=write_history(tmp_path)
    for hour,minute in ((21,10),(23,50)):
        result=run(history,tmp_path,at(hour,minute))
        assert result["new"] is False
        assert result["reason"]=="past_beijing_cutoff"


def test_frozen_issue_skips_without_time_or_source_cost(tmp_path):
    history=write_history(tmp_path)
    folder=tmp_path/"forecasts"
    folder.mkdir()
    (folder/"2026280.json").write_text(
        json.dumps({"type":"prospective-next-issue",
                    "target_issue":"2026280"}),encoding="utf-8")
    result=assess(history,folder,None,now=at(23,50))
    assert result["new"] is False and result["reason"]=="already_frozen"


def test_stale_freshness_prevents_backfill(tmp_path):
    history=write_history(tmp_path)
    now=at(0,30)
    old=now-timedelta(hours=26)
    result=run(history,tmp_path,now,old)
    assert result["reason"]=="stale_or_future_source" and not result["new"]
    recent=now-timedelta(hours=23)
    assert run(history,tmp_path,now,recent)["new"] is True
    future=now+timedelta(hours=1)
    assert run(history,tmp_path,now,future)["new"] is False


def test_malformed_existing_forecast_fails_closed(tmp_path):
    history=write_history(tmp_path)
    folder=tmp_path/"forecasts"
    folder.mkdir()
    (folder/"2026280.json").write_text(
        json.dumps({"target_issue":"2026279"}),encoding="utf-8")
    with pytest.raises(ValueError,match="invalid"):
        run(history,folder,at(6,20))


def test_explicit_beijing_deadline_and_clock_validation(tmp_path):
    history=write_history(tmp_path)
    with pytest.raises(ValueError,match="HH:MM"):
        assess(history,tmp_path,at(6,20).isoformat(),now=at(6,20),
               deadline_beijing="99:99")
    with pytest.raises(ValueError,match="timezone"):
        assess(history,tmp_path,at(6,20).isoformat(),
               now=datetime(2026,10,21,6,20))
    with pytest.raises(ValueError,match="source age"):
        assess(history,tmp_path,at(6,20).isoformat(),now=at(6,20),
               source_max_age_hours=50)
