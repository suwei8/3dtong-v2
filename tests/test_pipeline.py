import csv
import tempfile
from pathlib import Path
import pytest

from src.data.loader import load_history
from src.features.builder import feature_vector,build_dataset,WARMUP
from src.models.base import top3
from src.models.dtong_model import rule_top3
from src.pipeline.predict import issue_after
from src.pipeline.evaluate import evaluate

def history(n=120):
    return [{"Issue":str(2026001+i),"KaiJiang":f"{i%1000:03d}"} for i in range(n)]

def test_csv_sort_and_leading_zero(tmp_path):
    p=tmp_path/"data.csv"
    p.write_text("Issue,KaiJiang\n2026002,015\n2026001,280\n",encoding="utf-8")
    assert [r["KaiJiang"] for r in load_history(p)]==["280","015"]

def test_no_target_leakage():
    a=history()
    b=[dict(r) for r in a]
    b[100]["KaiJiang"]="999"
    assert (feature_vector(a[:100])==feature_vector(b[:100])).all()
    assert (feature_vector(a[:101])!=feature_vector(b[:101])).any()

def test_dataset_shape():
    X,Y=build_dataset(history())
    assert X.shape==(20,75)
    assert Y.shape==(20,10)
    assert Y[0,0]==1

def test_rule_and_horizon():
    assert len(set(rule_top3("123")))==3
    assert issue_after("2026263",10)=="2026273"
    with pytest.raises(ValueError):
        issue_after("2026360",10)

def test_metrics_without_unseen_draw():
    predictions={"last_known_issue":"2026263",
                 "predictions":[{"issue":"2026264","models":{"frequency-30":[0,1,2]}},
                                {"issue":"2026265","models":{"frequency-30":[0,1,2]}}]}
    results=evaluate(predictions,{"2026264":"015"})
    assert len(results)==1 and results[0]["hit"] is True
    assert results[0]["distinct_hit_count"]==2

def test_random_theory():
    assert abs(1-(.7**3)-.657)<1e-12
