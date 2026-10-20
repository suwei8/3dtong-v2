"""Prevent accidental publication of private data in the rolling research job."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_research_job_uses_private_checkout_and_only_aggregate_outputs():
    workflow=(ROOT/".github/workflows/rolling-research.yml").read_text(encoding="utf-8")
    assert "repository: suwei8/pinble-data" in workflow
    assert "secrets.PINBLE_DATA_TOKEN" in workflow
    assert "persist-credentials: false" in workflow
    assert "--holdout 200" in workflow
    assert "--include-current-models" in workflow
    assert 'len(body["variants"])==11' in workflow
    assert "git add -- reports/experimental/rolling-ablation.md reports/experimental/rolling-ablation.json reports/experimental/rolling-paired.md reports/experimental/rolling-paired.json" in workflow
    assert "git add -A" not in workflow
    assert "git add ." not in workflow
    assert "git add private-source" not in workflow
    assert "git add predictions/live" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "  schedule:" not in workflow


def test_research_workflow_does_not_touch_production_pipeline():
    workflow=(ROOT/".github/workflows/rolling-research.yml").read_text(encoding="utf-8")
    assert "src.pipeline.live" not in workflow
    assert "src.pipeline.evaluate_live" not in workflow
    assert "predictions/live/runs" not in workflow


def test_research_snapshot_and_paired_scoring_are_immutable_by_default():
    workflow=(ROOT/".github/workflows/rolling-research.yml").read_text(encoding="utf-8")
    assert "ref: 836f3c6016eafd5b9c0b6d1f8cb845ec34431383" in workflow
    assert 'git -C private-source rev-parse HEAD' in workflow
    assert "tests/test_paired_research.py" in workflow
    assert "rolling-paired.md" in workflow and "rolling-paired.json" in workflow
    assert 'paired["holdout_evaluated"] is False' in workflow
