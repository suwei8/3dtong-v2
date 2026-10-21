import json
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo

import pytest
from src.pipeline import opencode_live


def setup(monkeypatch,tmp_path,*,legacy=False):
    source={"target":"2026281","cutoff":"2026280","history":[
        {"Issue":f"2025{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,130)],
        "source_sha256":"digest"}
    monkeypatch.setattr(opencode_live,"load_live_history",lambda _:source)
    folder=tmp_path/"live"
    (folder/"runs").mkdir(parents=True)
    now=datetime.now(timezone.utc)
    parent={"type":"prospective-next-issue","target_issue":"2026281",
            "known_through_issue":"2026280",
            "generated_at_utc":(now-timedelta(minutes=3)).isoformat(),
            "models":{"ensemble":[0,1,2]}}
    if legacy:
        parent["models"]["opencode/a"]=[1,2,3]
    (folder/"runs"/"2026281.json").write_text(json.dumps(parent))
    return folder,now


def test_optional_needs_classical_parent_and_is_separate(monkeypatch,tmp_path):
    folder,now=setup(monkeypatch,tmp_path)
    monkeypatch.setattr(opencode_live,"compute_opencode_budget",lambda *a,**kw:240)
    from src.models.llm import opencode_free
    monkeypatch.setattr(opencode_free,"compete",lambda *args,**kwargs:{
        "opencode/a":{"model":"opencode/a","status":"ok","digits":[3,4,5]},
        "opencode/b":{"model":"opencode/b","status":"skipped","reason":"no network"}
    })
    assert opencode_live.freeze_optional("private",folder) is True
    extra=json.loads((folder/"opencode-runs"/"2026281.json").read_text())
    parent=json.loads((folder/"runs"/"2026281.json").read_text())
    assert parent["models"]=={"ensemble":[0,1,2]}
    assert extra["models"]["opencode/a"]==[3,4,5]
    assert "opencode/b" not in extra["models"]
    assert extra["derived_challengers"]["opencode-consensus"]["status"]=="skipped"
    assert extra["target_issue"]==parent["target_issue"]
    assert opencode_live.freeze_optional("private",folder) is False


def test_skips_when_no_parent_or_legacy_contains_llm(monkeypatch,tmp_path):
    folder,now=setup(monkeypatch,tmp_path,legacy=True)
    assert opencode_live.optional_preflight("private",folder,now=now)["reason"]=="legacy_embedded_opencode"
    (folder/"runs"/"2026281.json").unlink()
    assert opencode_live.optional_preflight("private",folder,now=now)["reason"]=="classical_forecast_not_ready"


def test_rejects_wrong_parent_cutoff_and_existing_record(tmp_path,monkeypatch):
    folder,now=setup(monkeypatch,tmp_path)
    parent=folder/"runs"/"2026281.json"
    old=json.loads(parent.read_text())
    old["known_through_issue"]="2026279"
    parent.write_text(json.dumps(old))
    with pytest.raises(ValueError,match="mismatch"):
        opencode_live.optional_preflight("private",folder,now=now)
    old["known_through_issue"]="2026280"
    parent.write_text(json.dumps(old))
    (folder/"opencode-runs").mkdir()
    (folder/"opencode-runs"/"2026281.json").write_text('{"target_issue":"2026281","type":"wrong"}')
    with pytest.raises(ValueError,match="invalid existing"):
        opencode_live.optional_preflight("private",folder,now=now)


def test_no_optional_voting_after_beijing_cutoff(monkeypatch,tmp_path):
    folder,now=setup(monkeypatch,tmp_path)
    late=datetime(2026,10,21,21,11,tzinfo=ZoneInfo("Asia/Shanghai"))
    assert opencode_live.optional_preflight("private",folder,now=late)["reason"]=="past_beijing_cutoff"
