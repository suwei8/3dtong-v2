"""Guard against regression: shallow checkout gives bogus CSV freshness timestamps."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_source_checkouts_are_not_shallow():
    for name in ("daily-predict.yml","operational-health.yml"):
        content=(ROOT/".github"/"workflows"/name).read_text(encoding="utf-8")
        assert "fetch-depth: 0" in content
        assert "git -C private-source log -1 --format=%cI -- data/k3_full_history.csv" in content


def test_schedule_only_prediction_workflow():
    content=(ROOT/".github"/"workflows"/"daily-predict.yml").read_text(encoding="utf-8")
    assert "  schedule:" in content and "  workflow_dispatch:" in content
    assert "  push:" not in content


def test_private_csv_not_published():
    ignore=(ROOT/".gitignore").read_text(encoding="utf-8")
    assert "private-source/" in ignore
