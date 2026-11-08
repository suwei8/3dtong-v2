import json
import pytest

from src.models.llm.vote_ensemble import CONSENSUS,HYBRID,combine_open_votes


def ok(key, digits):
    return {"model":key,"status":"ok","digits":digits}


def test_majority_vote():
    values={"kilo/a":ok("kilo/a",[1,3,6]),
            "kilo/b":ok("kilo/b",[1,3,8]),
            "kilo/c":ok("kilo/c",[1,3,9])}
    answer=combine_open_votes(values,[.1]*10)
    assert answer["predictions"][CONSENSUS][:2]==[1,3]
    assert len(set(answer["predictions"][HYBRID]))==3
    assert answer["statuses"][HYBRID]["llm_weight"]==.5


def test_model_ties_break_by_precutoff_ml():
    values={"kilo/a":ok("kilo/a",[0,1,2]),
            "kilo/b":ok("kilo/b",[3,4,5]),
            "kilo/c":ok("kilo/c",[6,7,8])}
    ml=[1]*10
    ml[8],ml[7],ml[6]=8,7,6
    assert combine_open_votes(values,ml)["predictions"][CONSENSUS]==[8,7,6]


def test_two_successful_models_cannot_fake_new_competitors():
    values={"kilo/a":ok("kilo/a",[0,1,2]),
            "kilo/b":ok("kilo/b",[1,2,3]),
            "kilo/c":{"model":"kilo/c","status":"skipped","reason":"rate limit"}}
    answer=combine_open_votes(values,[1]*10)
    assert answer["predictions"]=={}
    assert answer["statuses"][CONSENSUS]["status"]=="skipped"


@pytest.mark.parametrize("invalid",[
    {"model":"kilo/a","status":"ok","digits":[1,1,2]},
    {"model":"kilo/a","status":"ok","digits":[1,2,True]},
    {"model":"kilo/a","status":"ok","digits":[1,2,11]},
    {"model":"kilo/other","status":"ok","digits":[1,2,3]},
])
def test_reject_bad_successful_model_outputs(invalid):
    with pytest.raises(ValueError):
        combine_open_votes({"kilo/a":invalid},[1]*10)


def test_bad_statistical_scores():
    for bad in ([1]*9,[0]*10,[float("nan")]*10):
        with pytest.raises(ValueError):
            combine_open_votes({},bad)


def test_deterministic_independent_of_model_order():
    a={"kilo/a":ok("kilo/a",[0,1,2]),
       "kilo/b":ok("kilo/b",[1,3,4]),
       "kilo/c":ok("kilo/c",[4,5,6])}
    ml=list(range(1,11))
    assert combine_open_votes(a,ml)==combine_open_votes(dict(reversed(list(a.items()))),ml)
