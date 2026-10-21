"""The README is a display derived only from already-frozen public predictions."""
import json
from pathlib import Path

import pytest

from src.pipeline.readme_latest import (
    START, END, latest_seal, render_banner, update_readme,
)

ROOT = Path(__file__).resolve().parents[1]


def sample(issue="2026280", model="frequency-30"):
    return {
        "type": "prospective-next-issue",
        "target_issue": issue,
        "known_through_issue": f"{int(issue)-1:07d}",
        "generated_at_utc": "2026-10-20T17:13:31+00:00",
        "validation_selected_model": model,
        "models": {"frequency-30": [0,8,9], "xgboost": [6,8,0]},
    }


def write(root, data):
    folder = root / "runs"
    folder.mkdir(exist_ok=True)
    (folder / (data["target_issue"] + ".json")).write_text(
        json.dumps(data), encoding="utf-8")
    return folder


def test_insert_under_original_title_and_remain_idempotent(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\nOther content.\n", encoding="utf-8")
    folder = write(tmp_path, sample())
    assert update_readme(readme, folder, tmp_path/"optional")
    text = readme.read_text()
    assert text.startswith("# Project\n\n" + START)
    assert "**089**" in text and "验证集选定" in text
    assert "第 2026280 期" in text
    assert "2026-10-21 01:13:31" in text
    assert "Other content." in text
    assert not update_readme(readme, folder, tmp_path/"optional")
    assert text == readme.read_text()


def test_subsequent_new_seal_replaces_old_issue_without_duplication(tmp_path):
    readme = tmp_path/"README.md"
    readme.write_text("# Header\n\nExisting body\n", encoding="utf-8")
    folder = write(tmp_path, sample())
    update_readme(readme, folder)
    write(tmp_path, sample("2026281", "xgboost"))
    assert update_readme(readme, folder)
    view = readme.read_text()
    assert view.count(START) == view.count(END) == 1
    assert "第 2026281 期" in view
    assert "第 2026280 期" not in view
    assert "Existing body" in view
    assert "**680**" in view


def test_optional_models_are_included_but_original_seal_unchanged(tmp_path):
    readme = tmp_path/"README.md"
    readme.write_text("# Header\n\nBody\n")
    folder = write(tmp_path, sample())
    original = (folder/"2026280.json").read_bytes()
    optional = tmp_path/"opencode-runs"
    optional.mkdir()
    addon = {
        "type":"optional-opencode-contestants-v1",
        "target_issue":"2026280",
        "known_through_issue":"2026279",
        "classical_frozen_at_utc":"2026-10-20T17:13:31+00:00",
        "generated_at_utc":"2026-10-20T17:20:31+00:00",
        "models":{"opencode/example":[1,2,3]},
    }
    (optional/"2026280.json").write_text(json.dumps(addon))
    update_readme(readme, folder, optional)
    assert "| opencode/example | **123** |" in readme.read_text()
    assert "OpenCode 独立封存时间" in readme.read_text()
    assert original == (folder/"2026280.json").read_bytes()
    addon["models"]={"xgboost":[1,2,3]}
    (optional/"2026280.json").write_text(json.dumps(addon))
    with pytest.raises(ValueError, match="duplicate"):
        update_readme(readme, folder, optional)


def test_never_publish_unsealed_or_malformed_votes(tmp_path):
    readme = tmp_path/"README.md"
    readme.write_text("# Header\n\nBody\n")
    folder = write(tmp_path, sample())
    invalid = sample()
    invalid["models"]["xgboost"] = [1,1,2]
    (folder/"2026280.json").write_text(json.dumps(invalid))
    with pytest.raises(ValueError, match="three distinct"):
        update_readme(readme, folder)
    assert readme.read_text()=="# Header\n\nBody\n"


def test_incomplete_markers_must_not_duplicate_readme_sections(tmp_path):
    readme = tmp_path/"README.md"
    readme.write_text("# Header\n"+START+"\nMissing end\n")
    folder = write(tmp_path, sample())
    with pytest.raises(ValueError, match="incomplete"):
        update_readme(readme, folder)


def test_current_repository_readme_reflects_latest_real_immutable_seal():
    text = (ROOT/"README.md").read_text(encoding="utf-8")
    expected = render_banner(
        latest_seal(ROOT/"predictions/live/runs"),
        ROOT/"predictions/live/opencode-runs")
    assert expected in text
    assert text.count(START) == text.count(END) == 1
