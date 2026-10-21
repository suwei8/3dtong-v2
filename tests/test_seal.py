"""Simple genuine Git fixtures prove tampering fails without affecting stored forecasts."""
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path
import pytest

from src.pipeline.seal import verify_seals


def git(root,*args):
    subprocess.run(["git","-C",str(root),*args],check=True,
                   capture_output=True,text=True,timeout=10)


def create_fixture(tmp_path):
    git(tmp_path,"init")
    git(tmp_path,"config","user.name","CI")
    git(tmp_path,"config","user.email","ci@example.invalid")
    directory=tmp_path/"predictions"/"live"/"runs"
    directory.mkdir(parents=True)
    forecast={"type":"prospective-next-issue",
              "target_issue":"2026274","known_through_issue":"2026273",
              "generated_at_utc":datetime.now(timezone.utc).isoformat(),
              "models":{"baseline":[1,2,3]}}
    file=directory/"2026274.json"
    file.write_text(json.dumps(forecast),encoding="utf-8")
    git(tmp_path,"add","predictions/")
    git(tmp_path,"commit","-m","freeze issue")
    return file


def test_new_frozen_forecast_single_commit(tmp_path):
    create_fixture(tmp_path)
    result=verify_seals(tmp_path)
    assert len(result)==1 and result[0]["issue"]=="2026274"


def test_posthoc_overwrite_rejected(tmp_path):
    file=create_fixture(tmp_path)
    parsed=json.loads(file.read_text())
    parsed["models"]={"changed_after_result":[8,9,0]}
    file.write_text(json.dumps(parsed))
    git(tmp_path,"add","predictions/")
    git(tmp_path,"commit","-m","alter forecast")
    with pytest.raises(ValueError,match="exactly one"):
        verify_seals(tmp_path)


def test_uncommitted_forecast_change_rejected(tmp_path):
    file=create_fixture(tmp_path)
    file.write_text("{}")
    with pytest.raises(ValueError,match="uncommitted"):
        verify_seals(tmp_path)


def test_timestamp_must_match_original_git_commit(tmp_path):
    file=create_fixture(tmp_path)
    parsed=json.loads(file.read_text())
    parsed["generated_at_utc"]="2020-01-01T00:00:00+00:00"
    file.write_text(json.dumps(parsed))
    git(tmp_path,"add","predictions/")
    git(tmp_path,"commit","-m","try changing date")
    with pytest.raises(ValueError):
        verify_seals(tmp_path)



def test_independent_optional_seal_is_creation_only(tmp_path):
    original=create_fixture(tmp_path)
    folder=tmp_path/"predictions"/"live"/"opencode-runs"
    folder.mkdir()
    parent=json.loads(original.read_text())
    candidate={
        "type":"optional-opencode-contestants-v1",
        "target_issue":"2026274",
        "known_through_issue":"2026273",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "classical_frozen_at_utc":parent["generated_at_utc"],
        "models":{"opencode/a":[3,4,5]},
    }
    file=folder/"2026274.json"
    file.write_text(json.dumps(candidate))
    git(tmp_path,"add","predictions/live/opencode-runs")
    git(tmp_path,"commit","-m","seal independently")
    assert len(verify_seals(tmp_path,"predictions/live/opencode-runs",
                            "optional-opencode-contestants-v1"))==1
    candidate["models"]={"opencode/a":[6,7,8]}
    file.write_text(json.dumps(candidate))
    git(tmp_path,"add","predictions/live/opencode-runs")
    git(tmp_path,"commit","-m","tamper")
    with pytest.raises(ValueError,match="exactly one"):
        verify_seals(tmp_path,"predictions/live/opencode-runs",
                     "optional-opencode-contestants-v1")
