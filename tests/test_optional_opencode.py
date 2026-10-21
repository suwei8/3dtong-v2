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
    # Fixed 20:00 Beijing clock: tests must not depend on CI wall time.
    now=datetime(2026,10,21,12,0,tzinfo=timezone.utc)
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
    # Production cutoff stays 21:10. Freeze the test clock instead of
    # loosening that security boundary for nighttime GitHub CI runs.
    class FixedClock(datetime):
        @classmethod
        def now(cls,tz=None):
            return now.astimezone(tz) if tz is not None else now.replace(tzinfo=None)
    monkeypatch.setattr(opencode_live,"datetime",FixedClock)
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



def test_optional_cli_preflight_imports_without_site_packages():
    """Runs with -S (no site-packages): detection must work before pip install."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    project=Path(__file__).resolve().parents[1]
    result=subprocess.run(
        [sys.executable,"-S","-m","src.pipeline.opencode_live","--help"],
        cwd=project,
        env={**os.environ,"PYTHONPATH":str(project)},
        text=True,capture_output=True,timeout=12,check=False,
    )
    assert result.returncode==0, result.stderr
    assert "--preflight" in result.stdout


def test_optional_preflight_in_hermetic_python_skips_without_pip(tmp_path):
    import csv
    import os
    import subprocess
    import sys
    from pathlib import Path

    data=tmp_path/"historical.csv"
    with data.open("w",newline="",encoding="utf-8") as file:
        writer=csv.writer(file)
        writer.writerow(["Issue","KaiJiang"])
        for year,limit in [(2022,365),(2023,365),(2024,366),(2025,365),(2026,280)]:
            for seq in range(1,limit+1):
                writer.writerow([f"{year}{seq:03d}",f"{seq%1000:03d}"])
    root=tmp_path/"live"
    root.mkdir()
    output=tmp_path/"github_output"
    project=Path(__file__).resolve().parents[1]
    result=subprocess.run(
        [sys.executable,"-S","-m","src.pipeline.opencode_live",
         "--history",str(data),"--root",str(root),
         "--source-commit-utc","2026-10-21T06:00:00Z",
         "--github-output",str(output),"--preflight"],
        cwd=project,env={**os.environ,"PYTHONPATH":str(project)},
        text=True,capture_output=True,timeout=12,check=False,
    )
    assert result.returncode==0, result.stderr
    assert "reason=classical_forecast_not_ready" in output.read_text(encoding="utf-8")
