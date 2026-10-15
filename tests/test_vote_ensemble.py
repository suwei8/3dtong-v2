import json
import pytest

from src.models.llm.vote_ensemble import CONSENSUS,HYBRID,combine_open_votes
from src.pipeline.live import freeze_live


def ok(key, digits):
    return {"model":key,"status":"ok","digits":digits}


def test_majority_vote():
    values={"opencode/a":ok("opencode/a",[1,3,6]),
            "opencode/b":ok("opencode/b",[1,3,8]),
            "opencode/c":ok("opencode/c",[1,3,9])}
    answer=combine_open_votes(values,[.1]*10)
    assert answer["predictions"][CONSENSUS][:2]==[1,3]
    assert len(set(answer["predictions"][HYBRID]))==3
    assert answer["statuses"][HYBRID]["llm_weight"]==.5


def test_model_ties_break_by_precutoff_ml():
    values={"opencode/a":ok("opencode/a",[0,1,2]),
            "opencode/b":ok("opencode/b",[3,4,5]),
            "opencode/c":ok("opencode/c",[6,7,8])}
    ml=[1]*10
    ml[8],ml[7],ml[6]=8,7,6
    assert combine_open_votes(values,ml)["predictions"][CONSENSUS]==[8,7,6]


def test_two_successful_models_cannot_fake_new_competitors():
    values={"opencode/a":ok("opencode/a",[0,1,2]),
            "opencode/b":ok("opencode/b",[1,2,3]),
            "opencode/c":{"model":"opencode/c","status":"skipped","reason":"rate limit"}}
    answer=combine_open_votes(values,[1]*10)
    assert answer["predictions"]=={}
    assert answer["statuses"][CONSENSUS]["status"]=="skipped"


@pytest.mark.parametrize("invalid",[
    {"model":"opencode/a","status":"ok","digits":[1,1,2]},
    {"model":"opencode/a","status":"ok","digits":[1,2,True]},
    {"model":"opencode/a","status":"ok","digits":[1,2,11]},
    {"model":"opencode/other","status":"ok","digits":[1,2,3]},
])
def test_reject_bad_successful_model_outputs(invalid):
    with pytest.raises(ValueError):
        combine_open_votes({"opencode/a":invalid},[1]*10)


def test_bad_statistical_scores():
    for bad in ([1]*9,[0]*10,[float("nan")]*10):
        with pytest.raises(ValueError):
            combine_open_votes({},bad)


def test_deterministic_independent_of_model_order():
    a={"opencode/a":ok("opencode/a",[0,1,2]),
       "opencode/b":ok("opencode/b",[1,3,4]),
       "opencode/c":ok("opencode/c",[4,5,6])}
    ml=list(range(1,11))
    assert combine_open_votes(a,ml)==combine_open_votes(dict(reversed(list(a.items()))),ml)


def test_live_only_freezes_verified_votes(tmp_path,monkeypatch):
    from src.pipeline import live
    from src.models.llm import opencode_free
    monkeypatch.setattr(live,"load_live_history",lambda _: {
        "target":"2026275","cutoff":"2026274","source_sha256":"x",
        "pending_source_record":False,
        "history":[{"Issue":"2026274","KaiJiang":"015"}]})
    monkeypatch.setattr(live,"train_all",lambda _: {
        "scores":{},"champion_validation_only":"ensemble",
        "predictions":{"ensemble":[0,1,2]},
        "probabilities":{"ensemble":[.1]*10}})
    responses={"opencode/a":ok("opencode/a",[1,3,6]),
               "opencode/b":ok("opencode/b",[1,3,8]),
               "opencode/c":ok("opencode/c",[1,3,9])}
    monkeypatch.setattr(opencode_free,"compete",lambda *_a,**_kw:responses)
    assert freeze_live("not-read.csv",tmp_path/"live",opencode=True)
    sealed=tmp_path/"live"/"runs"/"2026275.json"
    before=sealed.read_bytes()
    record=json.loads(before)
    assert record["schema"]==5
    assert len(set(record["models"]["random-control-v1"]))==3
    assert CONSENSUS in record["models"] and HYBRID in record["models"]
    assert record["derived_challengers"][CONSENSUS]["status"]=="ok"
    assert not freeze_live("not-read.csv",tmp_path/"live",opencode=True)
    assert sealed.read_bytes()==before


def test_live_excludes_derived_when_models_unavailable(tmp_path,monkeypatch):
    from src.pipeline import live
    from src.models.llm import opencode_free
    monkeypatch.setattr(live,"load_live_history",lambda _: {
        "target":"2026275","cutoff":"2026274","source_sha256":"x",
        "pending_source_record":False,
        "history":[{"Issue":"2026274","KaiJiang":"015"}]})
    monkeypatch.setattr(live,"train_all",lambda _: {
        "scores":{},"champion_validation_only":"ensemble",
        "predictions":{"ensemble":[0,1,2]},
        "probabilities":{"ensemble":[.1]*10}})
    monkeypatch.setattr(opencode_free,"compete",lambda *_a,**_kw:{
        "opencode/a":ok("opencode/a",[1,2,3]),
        "opencode/b":{"model":"opencode/b","status":"skipped","reason":"timeout"}})
    assert freeze_live("not-read.csv",tmp_path/"live",opencode=True)
    item=json.loads((tmp_path/"live"/"runs"/"2026275.json").read_text())
    assert CONSENSUS not in item["models"] and HYBRID not in item["models"]
    assert item["derived_challengers"][HYBRID]["status"]=="skipped"
