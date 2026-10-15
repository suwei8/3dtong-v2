"""New hybrid challengers require their own denominators, without retroactive scores."""
import json
import pytest
from src.pipeline import evaluate_live as scoring


def create_forecast(folder,derived):
    fixture={
        "schema":4,"type":"prospective-next-issue",
        "target_issue":"2026275","known_through_issue":"2026274",
        "generated_at_utc":"2026-10-15T11:00:00+08:00",
        "models":{"ensemble":[1,2,3],"opencode/a":[0,5,6]},
        "opencode_challengers":{"opencode/a":{"status":"ok"},
                               "opencode/b":{"status":"skipped","reason":"timeout"}},
        "derived_challengers":derived
    }
    if derived["opencode-consensus"]["status"]=="ok":
        fixture["models"]["opencode-consensus"]=[0,1,4]
        fixture["models"]["ml-opencode-hybrid"]=[2,4,7]
    (folder/"2026275.json").write_text(json.dumps(fixture),encoding="utf-8")
    return fixture


def test_derived_success_scored_once_and_skip_coverage_preserved(tmp_path,monkeypatch):
    monkeypatch.setattr(scoring,"load_live_history",lambda _:{
        "history":[{"Issue":"2026275","KaiJiang":"407"}]})
    folder=tmp_path/"inputs"
    folder.mkdir()
    status={
        "opencode-consensus":{"status":"ok","contributors":["a","b","c"]},
        "ml-opencode-hybrid":{"status":"ok","contributors":["a","b","c"]}
    }
    create_forecast(folder,status)
    r=scoring.run("private-source.csv",folder,tmp_path/"reports")
    assert r["scored_issues"]==1 and r["frozen_issues"]==1
    assert r["models"]["opencode-consensus"]["hits"]==1
    assert r["models"]["ml-opencode-hybrid"]["hits"]==1
    assert r["models"]["opencode/a"]["hits"]==1
    assert r["models"]["opencode/b"]["unavailable"]==1
    assert r["models"]["opencode/b"]["published"]==0
    assert r==scoring.run("private-source.csv",folder,tmp_path/"reports")


def test_derived_insufficient_votes_not_counted_as_wrong(tmp_path,monkeypatch):
    monkeypatch.setattr(scoring,"load_live_history",lambda _:{
        "history":[{"Issue":"2026275","KaiJiang":"407"}]})
    folder=tmp_path/"inputs"
    folder.mkdir()
    unavailable={
        "opencode-consensus":{"status":"skipped","reason":"need 3"},
        "ml-opencode-hybrid":{"status":"skipped","reason":"need 3"}
    }
    create_forecast(folder,unavailable)
    result=scoring.run("data.csv",folder,tmp_path/"reports")
    for name in unavailable:
        assert result["models"][name]["published"]==0
        assert result["models"][name]["unavailable"]==1
        assert result["models"][name]["attempted"]==1


def test_illegal_derived_success_without_frozen_vote_fails(tmp_path,monkeypatch):
    monkeypatch.setattr(scoring,"load_live_history",lambda _:{
        "history":[{"Issue":"2026275","KaiJiang":"407"}]})
    folder=tmp_path/"inputs"
    folder.mkdir()
    status={
        "opencode-consensus":{"status":"ok"},
        "ml-opencode-hybrid":{"status":"skipped"}
    }
    create_forecast(folder,status)
    # By fixture helper, 'ok' adds both; remove hybrid to expose a mismatch.
    fixture=json.loads((folder/"2026275.json").read_text())
    del fixture["models"]["ml-opencode-hybrid"]
    fixture["derived_challengers"]["ml-opencode-hybrid"]={"status":"ok"}
    (folder/"2026275.json").write_text(json.dumps(fixture))
    with pytest.raises(ValueError,match="requires a frozen vote"):
        scoring.run("data.csv",folder,tmp_path/"reports")


def test_legacy_no_derived_metadata_still_works(tmp_path,monkeypatch):
    monkeypatch.setattr(scoring,"load_live_history",lambda _:{
        "history":[{"Issue":"2026275","KaiJiang":"407"}]})
    folder=tmp_path/"inputs"
    folder.mkdir()
    fixture=create_forecast(folder,{
        "opencode-consensus":{"status":"skipped"},
        "ml-opencode-hybrid":{"status":"skipped"}
    })
    del fixture["derived_challengers"]
    (folder/"2026275.json").write_text(json.dumps(fixture))
    assert scoring.run("data.csv",folder,tmp_path/"reports")["scored_issues"]==1
