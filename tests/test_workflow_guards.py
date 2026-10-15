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


def test_daily_predict_has_fallback_and_time_budget():
    content=(ROOT/".github"/"workflows"/"daily-predict.yml").read_text(encoding="utf-8")
    assert 'cron: "40 12 * * *"' in content
    assert '--opencode-max-seconds 240' in content
    assert '--publish-deadline-beijing 21:10' in content
    assert '--publish-reserve-seconds 120' in content
    assert 'timeout 120s npm install -g opencode-ai' in content
    assert 'if ! timeout' in content
    assert 'if: steps.target.outputs.new ==' in content


def test_last_minute_git_push_is_prevented():
    flow=(ROOT/".github"/"workflows"/"daily-predict.yml").read_text(encoding="utf-8")
    final_sync=flow.index("git pull --rebase origin main")
    final_push=flow.index("git push origin HEAD:main")
    assert final_sync<final_push
    guarded=flow[final_sync:final_push]
    assert 'hhmm=$(TZ=Asia/Shanghai date +%H%M)' in guarded
    assert 'if [ "$hhmm" -ge 2110 ]' in guarded
    assert 'exit 1' in guarded
