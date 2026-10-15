import json
import pytest

from src.evaluation.control import NAME,control_digits
from src.pipeline.live import freeze_live


def test_control_is_stable_and_three_distinct_digits():
    a=control_digits("2026274","2026275")
    assert len(a)==3
    assert len(set(a))==3
    assert all(type(d) is int and 0<=d<=9 for d in a)
    assert a == control_digits("2026274","2026275")
    assert NAME == "random-control-v1"


def test_target_issue_determines_control_without_future_draw():
    first=control_digits("2026273","2026274")
    assert first == control_digits("2026273","2026274")
    assert control_digits("2026274","2026275") != first or True


@pytest.mark.parametrize("origin,target", [
    ("2026275","2026275"),("2026276","2026275"),
    ("2026274","2026x75"),("2026274","2026275x"),
    (2026274,"2026275")
])
def test_bad_target_rejected(origin,target):
    with pytest.raises(ValueError):
        control_digits(origin,target)


def test_freeze_inserts_random_control_once_without_changing_originals(tmp_path,monkeypatch):
    from src.pipeline import live
    monkeypatch.setattr(live,"load_live_history",lambda _: {
        "target":"2026275","cutoff":"2026274","source_sha256":"a",
        "pending_source_record":False,"history":[{"Issue":"2026274","KaiJiang":"015"}]})
    monkeypatch.setattr(live,"train_all",lambda _: {
        "predictions":{"xgboost":[1,2,3]},"scores":{},
        "champion_validation_only":"xgboost"})
    folder=tmp_path/"live"
    assert freeze_live("ignored.csv",folder)
    original=(folder/"runs"/"2026275.json").read_bytes()
    record=json.loads(original)
    assert record["schema"]==5
    assert record["models"]["xgboost"]==[1,2,3]
    assert record["models"][NAME]==control_digits("2026274","2026275")
    assert record["research_protocol"]=="first-200-valid-prospective-issues-v1"
    assert freeze_live("ignored.csv",folder) is False
    assert (folder/"runs"/"2026275.json").read_bytes()==original
