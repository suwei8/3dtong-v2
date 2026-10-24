import json
import pytest
from src.evaluation.prospective_compare import audit,load_protocol,publish


def test_coverage_counts_missing_forecast_as_failure_but_not_future():
    scored=[
        {"target_issue":"2026274","scores":{"xgboost":True}},
        {"target_issue":"2026276","scores":{"xgboost":False}},
        {"target_issue":"2026278","scores":{"xgboost":True}},
    ]
    plan={"start_issue":"2026281","paired_target":200,
          "comparisons":[{"candidate":"xgboost","baseline":"frequency-30"}]}
    data=audit(["2026274","2026275","2026276","2026277","2026278"],
               ["2026274","2026276","2026278","2026279"],
               scored,protocol=plan)
    assert data["completed_source_issues"]==5
    assert data["sealed_completed_issues"]==3
    assert data["scored_completed_issues"]==3
    assert data["missed_completed_issues"]==["2026275","2026277"]
    assert data["forecast_coverage_pct"]==60
    assert data["scoring_coverage_pct"]==60
    assert data["pairs"]["xgboost__vs__frequency-30"]["shared_scored_issues"]==0


def test_joint_denominators_and_first_two_frozen_pairs_are_reproducible():
    plan={"start_issue":"2026281","paired_target":2,
          "comparisons":[{"candidate":"xgboost","baseline":"frequency-30"}]}
    completed=["2026280","2026281","2026282","2026283","2026284"]
    items=[
        {"target_issue":"2026280","scores":{"xgboost":False,"frequency-30":True}},
        {"target_issue":"2026281","scores":{"xgboost":True,"frequency-30":False}},
        {"target_issue":"2026282","scores":{"xgboost":False}},
        {"target_issue":"2026283","scores":{"xgboost":False,"frequency-30":True}},
        {"target_issue":"2026284","scores":{"xgboost":True,"frequency-30":True}},
    ]
    report=audit(completed,completed,items,protocol=plan,coverage_start="2026280")
    row=report["pairs"]["xgboost__vs__frequency-30"]
    assert row["shared_scored_issues"]==2
    assert row["joint_coverage_issues"]==3
    assert row["candidate_only_hits"]==1 and row["baseline_only_hits"]==1
    assert row["both_hit"]==0 and row["both_miss"]==0
    assert row["hit_rate_difference_pp"]==0
    assert row["confirmatory_p_value"] is None
    assert row["status"]=="fixed_window_full_descriptive"


def test_model_skips_do_not_count_as_misses(tmp_path):
    plan={"start_issue":"2026281","paired_target":200,
          "comparisons":[{"candidate":"opencode-consensus","baseline":"frequency-30"}]}
    results=[{"target_issue":"2026281","scores":{"frequency-30":True}},
             {"target_issue":"2026282","scores":{"frequency-30":False,
                                                  "opencode-consensus":True}}]
    report=audit(["2026281","2026282"],
                 ["2026281","2026282"],results,plan,coverage_start="2026281")
    pair=next(iter(report["pairs"].values()))
    assert pair["shared_scored_issues"]==1 and pair["candidate_only_hits"]==1
    assert pair["baseline_only_hits"]==0
    assert pair["confirmatory_p_value"] is None
    publish(report,tmp_path)
    md=(tmp_path/"live-paired.md").read_text(encoding="utf-8")
    obj=json.loads((tmp_path/"live-paired.json").read_text(encoding="utf-8"))
    assert obj==report
    assert "同期开奖" in md
    assert "KaiJiang" not in json.dumps(obj)+md
    assert "开奖号" not in json.dumps(obj)


def test_duplicates_and_integer_score_fail_closed():
    plan={"start_issue":"2026281","paired_target":200,
          "comparisons":[{"candidate":"xgboost","baseline":"frequency-30"}]}
    with pytest.raises(ValueError,match="duplicate"):
        audit(["2026281","2026281"],["2026281"],[],plan)
    with pytest.raises(ValueError,match="boolean"):
        audit(["2026281"],["2026281"],
              [{"target_issue":"2026281","scores":{"xgboost":1}}],plan)
    with pytest.raises(ValueError,match="nonsealed"):
        audit(["2026281"],[],
              [{"target_issue":"2026281","scores":{"xgboost":True}}],plan)


def test_fixed_prospective_pair_plan_starts_after_latest_frozen():
    plan=load_protocol()
    assert plan["start_issue"]=="2026281"
    assert plan["paired_target"]==200
    assert len(plan["comparisons"])==4


def test_scoring_completion_validation():
    plan={"start_issue":"2026281","paired_target":200,
          "comparisons":[{"candidate":"xgboost","baseline":"frequency-30"}]}
    with pytest.raises(ValueError,match="absent from completed"):
        audit(["2026281"],["2026281","2026282"],
              [{"target_issue":"2026282","scores":{"xgboost":True}}],plan)
    report=audit(["2026281"],["2026281"],[],plan,coverage_start="2026281")
    assert report["sealed_but_unscored_issues"]==["2026281"]


def test_llm_lightgbm_protocol_starts_after_scored_2026283():
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/"configs"/"llm_vs_ml_pair_protocol.json"
    plan=load_protocol(path)
    assert plan["start_issue"]=="2026284"
    assert plan["paired_target"]==200
    assert len(plan["comparisons"])==11
    assert {p["baseline"] for p in plan["comparisons"]}=={"lightgbm"}
    assert "opencode/space-bunny-free" not in {p["candidate"] for p in plan["comparisons"]}


def test_llm_lightgbm_paired_report_ignores_history_and_skips(tmp_path):
    from pathlib import Path
    plan=load_protocol(Path(__file__).resolve().parents[1]/"configs"/"llm_vs_ml_pair_protocol.json")
    records=[
        {"target_issue":"2026283","scores":{"opencode/longcat-2.5-preview-free":True,"lightgbm":False}},
        {"target_issue":"2026284","scores":{"opencode/longcat-2.5-preview-free":True,"opencode/mimo-v2.6-flash-free":False,"lightgbm":True}},
        {"target_issue":"2026285","scores":{"lightgbm":False}},
        {"target_issue":"2026286","scores":{"opencode/longcat-2.5-preview-free":False,"opencode/mimo-v2.6-flash-free":True,"lightgbm":True}}
    ]
    completed=["2026283","2026284","2026285","2026286"]
    report=audit(completed,completed,records,protocol=plan,coverage_start="2026283")
    longcat=report["pairs"]["opencode/longcat-2.5-preview-free__vs__lightgbm"]
    assert longcat["shared_scored_issues"]==2
    assert longcat["both_hit"]==1
    assert longcat["baseline_only_hits"]==1
    assert longcat["candidate_only_hits"]==0
    assert longcat["both_miss"]==0
    assert longcat["hit_rate_difference_pp"]==-50.0
    mimo=report["pairs"]["opencode/mimo-v2.6-flash-free__vs__lightgbm"]
    assert mimo["shared_scored_issues"]==2
    assert mimo["baseline_only_hits"]==1
    assert mimo["both_hit"]==1
    assert report["pairs"]["opencode/step-5-preview-free__vs__lightgbm"]["shared_scored_issues"]==0
    publish(report,tmp_path,file_stem="llm-vs-ml-paired",title="大模型 vs LightGBM")
    md=(tmp_path/"llm-vs-ml-paired.md").read_text(encoding="utf-8")
    obj=json.loads((tmp_path/"llm-vs-ml-paired.json").read_text(encoding="utf-8"))
    assert obj==report
    assert "大模型 vs LightGBM" in md
    assert "KaiJiang" not in md+json.dumps(obj)
    assert not (tmp_path/"live-paired.md").exists()
