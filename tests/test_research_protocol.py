import json
import math
import pytest
from src.evaluation.research import (
    exact_binomial_upper_tail, load_protocol,
    analyze_scored_frozen_issues, publish_research,
)


def minimal_protocol():
    return {
        "name":"fixed-3-demo-v1",
        "start_issue":"2026275",
        "sample_size_per_registered_model":3,
        "null_hit_probability":0.657,
        "one_sided_alpha":0.05,
        "planned_models":["a","b"],
        "observational_control":"random-control-v1",
    }


def test_exact_binomial_tail():
    assert exact_binomial_upper_tail(0,0,.657)==1
    assert exact_binomial_upper_tail(1,1,.657)==pytest.approx(.657)
    assert exact_binomial_upper_tail(2,2,.657)==pytest.approx(.657**2)
    assert exact_binomial_upper_tail(1,2,.657)==pytest.approx(1-.343**2)
    assert exact_binomial_upper_tail(100,100,.657)==pytest.approx(.657**100)
    with pytest.raises(ValueError):
        exact_binomial_upper_tail(3,2,.657)


def test_no_early_statistical_testing():
    obj=[{"target_issue":"2026275","scores":{"a":True,"b":False,"random-control-v1":True}}]
    report=analyze_scored_frozen_issues(obj,minimal_protocol())
    assert report["models"]["a"]["bonferroni_p"] is None
    assert report["models"]["b"]["passes_bonferroni_threshold"] is None
    assert report["models"]["random-control-v1"]["raw_p_one_sided"] is None


def test_immutable_first_fixed_window_and_multiplicity():
    obj=[
        {"target_issue":f"202627{i}","scores":{
            "a":True,"b":False,"random-control-v1":bool(i%2)}}
        for i in range(5,9)
    ]
    report=analyze_scored_frozen_issues(obj,minimal_protocol())
    a=report["models"]["a"]
    assert a["first_horizon_valid_votes"]==3 and a["hits_in_window"]==3
    assert a["bonferroni_p"]==pytest.approx(min(1,2*.657**3))
    assert report["models"]["b"]["hits_in_window"]==0
    assert report["models"]["b"]["bonferroni_p"]==1
    assert report["models"]["random-control-v1"]["bonferroni_p"] is None


def test_older_published_issues_never_enter_future_window():
    values=[{"target_issue":"2026274","scores":{"a":True}},
            {"target_issue":"2026275","scores":{"a":False}}]
    report=analyze_scored_frozen_issues(values,minimal_protocol())
    assert report["completed_prospective_issues_in_scope"]==1
    assert report["models"]["a"]["hits_in_window"]==0


def test_unavailable_votes_have_no_denominator_and_no_fabricated_hit():
    values=[
        {"target_issue":"2026275","scores":{"a":True,"b":False}},
        {"target_issue":"2026276","scores":{"a":True}},
        {"target_issue":"2026277","scores":{"a":False,"b":True}},
    ]
    report=analyze_scored_frozen_issues(values,minimal_protocol())
    assert report["models"]["a"]["first_horizon_valid_votes"]==3
    assert report["models"]["b"]["first_horizon_valid_votes"]==2
    assert report["models"]["b"]["bonferroni_p"] is None


def test_reject_duplicate_and_non_boolean_metrics():
    r=[{"target_issue":"2026275","scores":{"a":True}}]*2
    with pytest.raises(ValueError,match="twice"):
        analyze_scored_frozen_issues(r,minimal_protocol())
    with pytest.raises(ValueError,match="boolean"):
        analyze_scored_frozen_issues([{"target_issue":"2026275","scores":{"a":1}}],minimal_protocol())


def test_published_research_never_contains_raw_codes(tmp_path):
    publication=publish_research(
        [{"target_issue":"2026275","scores":{"a":True,"random-control-v1":False}}],
        tmp_path,minimal_protocol()
    )
    saved=(tmp_path/"research.md").read_text(encoding="utf-8")
    assert publication["models"]["a"]["window_complete"] is False
    assert "KaiJiang" not in saved
    assert "015" not in saved
    parsed=json.loads((tmp_path/"research.json").read_text(encoding="utf-8"))
    assert parsed["multiple_comparison_factor"]==2


def test_real_preregistered_family_size():
    protocol=load_protocol()
    assert protocol["sample_size_per_registered_model"]==200
    assert protocol["start_issue"]=="2026275"
    assert len(protocol["planned_models"])==17
    assert "random-control-v1" not in protocol["planned_models"]
