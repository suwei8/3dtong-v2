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


def test_readable_history_is_rendered_by_prediction_and_evaluation_workflows():
    predict=(ROOT/".github"/"workflows"/"daily-predict.yml").read_text(encoding="utf-8")
    evaluate=(ROOT/".github"/"workflows"/"daily-evaluate.yml").read_text(encoding="utf-8")
    renderer="python -m src.pipeline.render_history"
    assert renderer in predict and renderer in evaluate
    assert "predictions/live/HISTORY.md" in predict and "predictions/live/history/" in predict
    assert "predictions/live/HISTORY.md" in evaluate and "predictions/live/history/" in evaluate



def test_daily_evaluation_publishes_aggregate_pair_and_coverage_report():
    wf=(ROOT/".github"/"workflows"/"daily-evaluate.yml").read_text(encoding="utf-8")
    scorer=(ROOT/"src"/"pipeline"/"evaluate_live.py").read_text(encoding="utf-8")
    assert "reports/live-paired.md reports/live-paired.json" in wf
    assert '"src/evaluation/prospective_compare.py"' in wf
    assert '"configs/live_pair_protocol.json"' in wf
    assert "publish_pairs(audit(" in scorer
    assert "git add -A" not in wf



def test_prediction_fast_preflight_precedes_package_installation_and_has_day_retries():
    flow=(ROOT/".github"/"workflows"/"daily-predict.yml").read_text(encoding="utf-8")
    for schedule in (
        'cron: "30 16 * * *"', # Beijing 00:30
        'cron: "20 22 * * *"', # Beijing 06:20
        'cron: "20 4 * * *"',  # Beijing 12:20
        'cron: "20 9 * * *"',  # Beijing 17:20
        'cron: "50 11 * * *"', # Beijing 19:50
        'cron: "20 12 * * *"', # Beijing 20:20
        'cron: "40 12 * * *"', # Beijing 20:40
    ):
        assert schedule in flow
    assert flow.index("python -m src.pipeline.preflight") < flow.index("actions/setup-python@v5")
    assert flow.index("actions/setup-python@v5") < flow.index("python -m pip install -r requirements.txt")
    assert '--max-source-age-hours 24' in flow
    assert '--deadline-beijing 21:10' in flow
    assert 'if: steps.target.outputs.new ==' in flow
    assert '  push:' not in flow
    assert "python -m pytest -q tests/" not in flow
    assert 'git add predictions/live/LATEST.md' in flow
    assert 'git add private-source' not in flow
