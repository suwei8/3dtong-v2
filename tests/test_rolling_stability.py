"""Time-segment diagnostics: no individual period or holdout details are emitted."""
import json
from dataclasses import replace
import pytest

from src.research.stability import analyze_stability,render_markdown
from src.research.rolling import Config,walk_forward,publish


def make_study():
    cfg=Config(holdout_size=20,development_rounds=12,
               refit_interval=3,min_training_rows=90)
    return {"config":cfg,"hits":{
        "full":[True]*6+[False]*6,
        "frequency-30":[True,True,False]*4,
        "sha256-random-control":[False]*12,
        "without_frequency":[False]*6+[True]*6,
        "xgboost":[True]*3+[False]*3+[True]*3+[False]*3,
    }}


def test_stability_blocks_are_chronological_and_complete():
    obj=analyze_stability(make_study())
    assert obj["segment_size"]==3 and obj["segment_count"]==4
    assert [b["model_hits"]["full"] for b in obj["blocks"]]==[3,3,0,0]
    assert [b["model_hits"]["xgboost"] for b in obj["blocks"]]==[3,0,3,0]
    assert obj["adoption_approved"] is False and obj["holdout_evaluated"] is False
    assert "2023" not in json.dumps(obj)


def test_disjoint_windows_match_exact_full_pair_counts():
    study=make_study()
    result=analyze_stability(study)
    for pair in result["comparisons"].values():
        assert pair["better_segments"]+pair["worse_segments"]+pair["tied_segments"]==4
        for item in pair["segments"]:
            assert sum(item[k] for k in ("candidate_only","reference_only","both_hit","both_miss"))==3
        assert pair["total_net_hits"]==sum(study["hits"][pair["candidate"]])-sum(
            study["hits"][pair["baseline"]])


def test_optional_xgboost_is_omitted_not_invented():
    study=make_study()
    del study["hits"]["xgboost"]
    result=analyze_stability(study)
    assert not any(key.startswith("xgboost") for key in result["comparisons"])
    assert "without_frequency_vs_full" in result["comparisons"]


def test_reject_invalid_or_not_aligned_sample_periods():
    data=make_study()
    with pytest.raises(ValueError,match="complete refit blocks"):
        analyze_stability({**data,"config":replace(data["config"],refit_interval=5)})
    data["hits"]["frequency-30"]=[True]*11
    with pytest.raises(ValueError,match="every development period"):
        analyze_stability(data)


def test_readable_document_excludes_draw_codes_or_period_predictions():
    result=analyze_stability(make_study())
    text=render_markdown(result)
    assert "时间区间" in text and "第4段" in text
    assert "隔离区" in text
    assert "KaiJiang" not in text+json.dumps(result)
    assert "2026279" not in text+json.dumps(result)


def test_holdout_modifications_cannot_change_stability_report():
    history=[{"Issue":f"2023{i:03d}","KaiJiang":f"{(i*37+13)%1000:03d}"}
             for i in range(1,261)]
    cfg=Config(holdout_size=20,development_rounds=20,
               refit_interval=5,min_training_rows=90)
    a=analyze_stability(walk_forward(history,cfg))
    changed=[dict(v) for v in history]
    for row in changed[-20:]:
        row["KaiJiang"]="999"
    assert a==analyze_stability(walk_forward(changed,cfg))


def test_published_lightweight_study_has_stability_but_not_fake_model(tmp_path):
    history=[{"Issue":f"2023{i:03d}","KaiJiang":f"{(i*37+13)%1000:03d}"}
             for i in range(1,261)]
    cfg=Config(holdout_size=20,development_rounds=20,
               refit_interval=5,min_training_rows=90)
    publish(walk_forward(history,cfg),tmp_path)
    assert (tmp_path/"rolling-stability.md").exists()
    obj=json.loads((tmp_path/"rolling-stability.json").read_text())
    assert obj["segment_count"]==4
    assert obj["adoption_approved"] is False
    assert not any(x.startswith("xgboost") for x in obj["comparisons"])
