"""Wall-clock budget is fixed before scores are revealed.

These unit tests use mock model replies; never invoke Kilo or private CSV.
"""
import json
import pytest

from src.models.llm import kilo_free


def fake_history():
    return [{"Issue":f"2025{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,130)]


def test_budget_exhaustion_skips_remaining_models(monkeypatch):
    models=["kilo/a","kilo/b","kilo/c"]
    ticks=iter([0.0,0.1,1.1,20.0,20.1])
    monkeypatch.setattr(kilo_free,"load_models",lambda: (models,20))
    called=[]
    def fake_predict(summary,model,timeout):
        called.append((model,timeout))
        return {"model":model,"status":"ok","digits":[0,1,2]}
    monkeypatch.setattr(kilo_free,"predict_model",fake_predict)
    result=kilo_free.compete(fake_history(),budget_seconds=22,clock=lambda:next(ticks))
    assert [name for name,_ in called]==["kilo/a","kilo/b"]
    assert all(5<=timeout<=20 for _,timeout in called)
    assert result["kilo/c"]["status"]=="skipped"
    assert result["kilo/c"]["reason"]=="overall Kilo budget exhausted"


def test_model_budget_cannot_be_negative_or_too_large(monkeypatch):
    monkeypatch.setattr(kilo_free,"load_models",lambda: (
        ["kilo/a"],45))
    for budget in (-1,1801,"1"):
        with pytest.raises(ValueError,match="budget"):
            kilo_free.compete(fake_history(),budget_seconds=budget)


def test_model_ids_are_allowlisted_and_duplicate_rejected(monkeypatch):
    monkeypatch.setattr(kilo_free,"load_models",lambda: (
        ["kilo/a","kilo/b"],45))
    with pytest.raises(ValueError,match="approved"):
        kilo_free.compete(fake_history(),models=["not-a-provider"])
    with pytest.raises(ValueError,match="duplicate"):
        kilo_free.compete(fake_history(),models=["kilo/a","kilo/a"])


def test_default_path_remains_normal_when_no_budget_is_requested(monkeypatch):
    monkeypatch.setattr(kilo_free,"load_models",lambda: (
        ["kilo/a"],45))
    monkeypatch.setattr(kilo_free,"predict_model",lambda s,m,timeout: {
        "model":m,"status":"ok","digits":[1,2,3]})
    assert kilo_free.compete(fake_history())["kilo/a"]["status"]=="ok"
