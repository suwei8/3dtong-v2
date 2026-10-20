import json
from src.research.paired import exact_mcnemar_two_sided,paired_comparison,analyze_study,render_markdown
import pytest


def test_exact_mcnemar_no_discordance_and_simple_facts():
    assert exact_mcnemar_two_sided(0,0)==1
    assert exact_mcnemar_two_sided(1,0)==1
    assert exact_mcnemar_two_sided(2,0)==pytest.approx(.5)
    assert exact_mcnemar_two_sided(3,0)==pytest.approx(.25)
    assert exact_mcnemar_two_sided(2,2)==1
    assert exact_mcnemar_two_sided(9,1)==pytest.approx(22/1024)
    with pytest.raises(ValueError):
        exact_mcnemar_two_sided(-1,0)


def test_match_table_all_cells_and_exact_rate_gap():
    a=[True, True, False, False]*10
    b=[True, False, True, False]*10
    result=paired_comparison(a,b)
    assert (result["both_hit"],result["candidate_only_hit"],
            result["baseline_only_hit"],result["both_miss"])==(10,10,10,10)
    assert result["candidate_minus_baseline_percentage_points"]==0
    assert result["mcnemar_two_sided_p_exploratory"]==1
    assert result["samples"]==40 and result["confirmatory"] is False


def test_bootstrap_is_deterministic_and_detects_extreme_advantage():
    a=[True]*30
    b=[False]*30
    first=paired_comparison(a,b,block_length=10,replications=1000)
    assert first==paired_comparison(a,b,block_length=10,replications=1000)
    assert first["paired_circular_block_bootstrap_95_gap_pp"]==[100.,100.]
    assert first["candidate_only_hit"]==30 and first["baseline_only_hit"]==0


def test_inputs_must_be_equal_boolean_vectors_and_valid_settings():
    for a,b in (([],[]),([True],[True,False]),([1],[False]),([True],[0])):
        with pytest.raises(ValueError):
            paired_comparison(a,b)
    with pytest.raises(ValueError):
        paired_comparison([True]*20,[False]*20,replications=100)


def test_exploratory_protocol_does_not_print_period_votes_or_private_fields():
    study={"hits":{
        "xgboost":[True,False,True,False]*30,
        "frequency-30":[True,True,False,False]*30,
        "sha256-random-control":[False,False,True,True]*30,
        "without_frequency":[True]*120,
        "full":[False]*120,
    }}
    report=analyze_study(study)
    assert len(report["comparisons"])==3
    assert report["holdout_evaluated"] is False
    assert report["production_modified"] is False
    for row in report["comparisons"].values():
        assert sum(row[k] for k in ("both_hit","both_miss",
                                  "candidate_only_hit","baseline_only_hit"))==120
    document=render_markdown(report)
    assert "McNemar" in document and "隔离区" in document
    assert "KaiJiang" not in document+json.dumps(report)
    assert "2023279" not in document+json.dumps(report)
