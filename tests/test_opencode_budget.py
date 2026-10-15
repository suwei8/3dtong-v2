"""Wall-clock budget is fixed before scores are revealed.

These unit tests use mock model replies; never invoke OpenCode or private CSV.
"""
import json
import pytest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo

from src.models.llm import opencode_free
from src.pipeline import live


def fake_history():
    return [{"Issue":f"2025{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,130)]


def test_budget_exhaustion_skips_remaining_models(monkeypatch):
    models=["opencode/a","opencode/b","opencode/c"]
    ticks=iter([0.0,0.1,1.1,20.0,20.1])
    monkeypatch.setattr(opencode_free,"load_models",lambda: (models,20))
    called=[]
    def fake_predict(summary,model,timeout):
        called.append((model,timeout))
        return {"model":model,"status":"ok","digits":[0,1,2]}
    monkeypatch.setattr(opencode_free,"predict_model",fake_predict)
    result=opencode_free.compete(fake_history(),budget_seconds=22,clock=lambda:next(ticks))
    assert [name for name,_ in called]==["opencode/a","opencode/b"]
    assert all(5<=timeout<=20 for _,timeout in called)
    assert result["opencode/c"]["status"]=="skipped"
    assert result["opencode/c"]["reason"]=="overall OpenCode budget exhausted"


def test_zero_budget_keeps_legacy_classical_models_intact(monkeypatch,tmp_path):
    monkeypatch.setattr(live,"load_live_history",lambda _: {
        "target":"2026275","cutoff":"2026274","source_sha256":"abc",
        "pending_source_record":False,"history":fake_history()})
    monkeypatch.setattr(live,"train_all",lambda _: {
        "scores":{},"champion_validation_only":"xgboost",
        "predictions":{"xgboost":[1,2,3]},
        "probabilities":{"ensemble":[.1]*10}})
    monkeypatch.setattr(opencode_free,"load_models",lambda: (
        ["opencode/a","opencode/b","opencode/c"],45))
    monkeypatch.setattr(opencode_free.shutil,"which",lambda _:None)
    assert live.freeze_live("none.csv",tmp_path/"live",opencode=True,
                            opencode_max_seconds=0)
    result=json.loads((tmp_path/"live"/"runs"/"2026275.json").read_text())
    assert result["models"]["xgboost"]==[1,2,3]
    assert len(result["models"]["random-control-v1"])==3
    for item in result["opencode_challengers"].values():
        assert item["status"]=="skipped"
        assert item["reason"]=="overall OpenCode budget exhausted"
    assert result["derived_challengers"]["opencode-consensus"]["status"]=="skipped"


def test_model_budget_cannot_be_negative_or_too_large(monkeypatch):
    monkeypatch.setattr(opencode_free,"load_models",lambda: (
        ["opencode/a"],45))
    for budget in (-1,1801,"1"):
        with pytest.raises(ValueError,match="budget"):
            opencode_free.compete(fake_history(),budget_seconds=budget)


def test_model_ids_are_allowlisted_and_duplicate_rejected(monkeypatch):
    monkeypatch.setattr(opencode_free,"load_models",lambda: (
        ["opencode/a","opencode/b"],45))
    with pytest.raises(ValueError,match="approved"):
        opencode_free.compete(fake_history(),models=["not-a-provider"])
    with pytest.raises(ValueError,match="duplicate"):
        opencode_free.compete(fake_history(),models=["opencode/a","opencode/a"])


def test_default_path_remains_normal_when_no_budget_is_requested(monkeypatch):
    monkeypatch.setattr(opencode_free,"load_models",lambda: (
        ["opencode/a"],45))
    monkeypatch.setattr(opencode_free,"predict_model",lambda s,m,timeout: {
        "model":m,"status":"ok","digits":[1,2,3]})
    assert opencode_free.compete(fake_history())["opencode/a"]["status"]=="ok"
