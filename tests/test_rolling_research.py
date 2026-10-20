"""All test data is synthetic; never loads private CSV or future production outcomes."""
import json
from dataclasses import replace
import pytest
from src.research.rolling import Config, FEATURE_GROUPS, VARIANTS, walk_forward, aggregate, publish


def synthetic(n=260):
    return [{"Issue":f"2023{i:03d}","KaiJiang":f"{(i*37+13)%1000:03d}"}
            for i in range(1,n+1)]


def config():
    return Config(holdout_size=20,development_rounds=20,
                  refit_interval=5,min_training_rows=90,ridge_alpha=25.0)


def test_feature_masks_are_exhaustive_nonoverlapping_75_dimensions():
    assert [len(v) for v in FEATURE_GROUPS.values()]==[30,10,30,5]
    assert sorted(x for group in FEATURE_GROUPS.values() for x in group)==list(range(75))
    assert len(VARIANTS)==6


def test_rolling_labels_and_votes_have_identical_period_coverage():
    study=walk_forward(synthetic(),config())
    assert len(study["trace"])==20 and len(study["hits"])==8
    assert all(len(scores)==20 for scores in study["hits"].values())
    assert all(len(set(v))==3 for row in study["trace"] for v in row["votes"].values())
    assert all(int(row["trained_through"])<int(row["issue"]) for row in study["trace"])


def test_modifying_any_holdout_draw_cannot_change_a_single_development_prediction():
    a=synthetic()
    b=[dict(row) for row in a]
    for row in b[-20:]:
        row["KaiJiang"]="999"
    x=walk_forward(a,config())
    y=walk_forward(b,config())
    assert x["trace"]==y["trace"]
    assert aggregate(x)==aggregate(y)


def test_changed_target_label_does_not_change_its_own_prediction():
    a=synthetic()
    b=[dict(row) for row in a]
    b[-21]["KaiJiang"]="999"
    assert walk_forward(a,config())["trace"][-1]["votes"]==walk_forward(b,config())["trace"][-1]["votes"]


def test_insufficient_history_refused_after_holdout_reservation():
    with pytest.raises(ValueError,match="not enough history"):
        walk_forward(synthetic(),replace(config(),holdout_size=200))


def test_unsorted_issues_rejected():
    rows=synthetic()
    rows[2],rows[3]=rows[3],rows[2]
    with pytest.raises(ValueError,match="oldest-first"):
        walk_forward(rows,config())


def test_reports_contain_only_aggregates(tmp_path):
    report=publish(walk_forward(synthetic(),config()),tmp_path)
    json_text=(tmp_path/"rolling-ablation.json").read_text()
    md=(tmp_path/"rolling-ablation.md").read_text()
    assert json.loads(json_text)==report
    assert len(report["variants"])==8
    assert report["safety"]["holdout_used_in_training_or_scoring"] is False
    assert "KaiJiang" not in json_text+md
    assert "2023240" not in json_text+md
    assert "50" not in report["kind"]
    assert "滚动回测" in md


def test_invalid_configuration_refused():
    for bad in (replace(config(),ridge_alpha=float("nan")),
                replace(config(),refit_interval=0),
                replace(config(),min_training_rows=20)):
        with pytest.raises(ValueError):
            walk_forward(synthetic(),bad)



def test_optional_existing_models_see_only_preblock_training_data(monkeypatch):
    import numpy as np
    training_sizes=[]
    class DummyExistingModel:
        def fit(self,X,Y):
            training_sizes.append((len(X),len(Y)))
            self.bias=Y.mean(axis=0)
            return self
        def predict_proba(self,X):
            return np.tile(self.bias,(len(X),1))
    result=walk_forward(synthetic(),config(),additional_models={"existing-ml":DummyExistingModel})
    assert len(result["hits"]["existing-ml"])==20
    # After 100 warmup draws, the first development target is index220.
    # Thus first fit has 120 training labels; final refit has 135.
    assert training_sizes==[(120,120),(125,125),(130,130),(135,135)]
    assert all(len(row["votes"]["existing-ml"])==3 for row in result["trace"])
    changed=synthetic()
    for row in changed[-20:]:
        row["KaiJiang"]="999"
    assert result["trace"]==walk_forward(
        changed,config(),additional_models={"existing-ml":DummyExistingModel})["trace"]


def test_invalid_extra_model_names_are_rejected():
    with pytest.raises(ValueError,match="additional models"):
        walk_forward(synthetic(),config(),additional_models={"full":lambda:None})
