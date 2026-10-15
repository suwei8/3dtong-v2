"""Publish-reserved OpenCode time budget, including delayed scheduled runners."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from src.pipeline.live import compute_opencode_budget


BJ=ZoneInfo("Asia/Shanghai")


@pytest.mark.parametrize("hour,minute,expected",[
    (19,50,240), # lots of time; global 4-minute cap
    (20,40,240), # 30 min remain, no need to reduce
    (21,4,240),  # 6 minutes remain => 4-minute cap
    (21,5,180),  # 5 minutes remain => 3 minutes for model
    (21,7,60),   # 3 minutes remain => 1 minute for model
    (21,8,0),    # 2 minutes remain => reserve all for publishing
    (21,12,0),   # missed deadline; must not roll to tomorrow
])
def test_budget_never_pushes_model_into_publication_reserve(hour,minute,expected):
    current=datetime(2026,10,15,hour,minute,tzinfo=BJ)
    assert compute_opencode_budget(240,"21:10",120,current)==expected


def test_explicit_budget_without_deadline():
    assert compute_opencode_budget(120)==120
    assert compute_opencode_budget(None) is None


def test_utc_clock_is_converted_to_beijing():
    utc=ZoneInfo("UTC")
    moment=datetime(2026,10,15,13,7,tzinfo=utc)
    assert compute_opencode_budget(240,"21:10",120,moment)==60


@pytest.mark.parametrize("budget,reserve",[
    (-1,120),(2000,120),(240,-1),(240,9999),("240",120)
])
def test_invalid_budget_or_reserve_fails_closed(budget,reserve):
    with pytest.raises(ValueError):
        compute_opencode_budget(budget,"21:10",reserve,
                                datetime(2026,10,15,20,40,tzinfo=BJ))


def test_naive_clock_is_not_silently_treated_as_beijing():
    with pytest.raises(ValueError,match="timezone-aware"):
        compute_opencode_budget(240,"21:10",120,datetime(2026,10,15,20,40))
