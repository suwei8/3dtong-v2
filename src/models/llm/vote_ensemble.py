"""Fixed, pre-result OpenCode ensemble contestants.

No actual winning digits or validation outcomes are used in model voting.
The same recipe is applied at every subsequent new issue.
"""
import math
from collections import Counter

CONSENSUS = "opencode-consensus"
HYBRID = "ml-opencode-hybrid"
MIN_PARTICIPANTS = 3
LLM_WEIGHT = 0.5


def _valid_digits(value):
    return (isinstance(value,list) and len(value)==3
            and all(type(d) is int and 0<=d<=9 for d in value)
            and len(set(value))==3)


def _normalise_ml(probs):
    if (not isinstance(probs,(list,tuple)) or len(probs)!=10
            or any(type(p) not in (int,float) or not math.isfinite(p) or p<0
                   for p in probs)):
        raise ValueError("expected ten nonnegative finite ML probabilities")
    total=sum(probs)
    if total<=0:
        raise ValueError("ML probabilities are all zero")
    return [p/total for p in probs]


def combine_open_votes(results, ml_probabilities, min_participants=MIN_PARTICIPANTS):
    """Return new digits ONLY when >=3 validated real OpenCode contenders succeed.

    Consensus: each model votes once for each of its three distinct digits;
    ties are broken by pre-cutoff ML ensemble probabilities, then digit ID.
    Hybrid: 50% normalized vote presence distribution + 50% normalized ML
    probability distribution. This fixed blend is NOT tuned to future results.
    """
    if type(min_participants) is not int or min_participants<3:
        raise ValueError("minimum participants cannot be below 3")
    ml=_normalise_ml(ml_probabilities)
    if not isinstance(results,dict):
        raise ValueError("model outputs must be a mapping")
    accepted={}
    for name,answer in sorted(results.items()):
        if not isinstance(name,str) or not name.startswith("opencode/"):
            raise ValueError("invalid OpenCode model identity")
        if not isinstance(answer,dict):
            raise ValueError("invalid OpenCode output")
        if answer.get("status")!="ok":
            continue
        if answer.get("model")!=name or not _valid_digits(answer.get("digits")):
            raise ValueError("invalid successful model output")
        accepted[name]=answer["digits"]
    contributors=sorted(accepted)
    forecasts={}
    metadata={}
    if len(contributors)<min_participants:
        for name in (CONSENSUS,HYBRID):
            metadata[name]={"status":"skipped","contributors":contributors,
                            "reason":f"require {min_participants} verified models; got {len(contributors)}"}
        return {"predictions":forecasts,"statuses":metadata}

    n=len(contributors)
    counts=Counter(d for selection in accepted.values() for d in selection)
    forecasts[CONSENSUS]=sorted(range(10),key=lambda d:(-counts[d],-ml[d],d))[:3]
    blended=[LLM_WEIGHT*counts[d]/(3*n)+(1-LLM_WEIGHT)*ml[d] for d in range(10)]
    forecasts[HYBRID]=sorted(range(10),key=lambda d:(-blended[d],d))[:3]
    metadata[CONSENSUS]={"status":"ok","contributors":contributors,
                         "method":"equal votes; pre-cutoff ML breaks ties"}
    metadata[HYBRID]={"status":"ok","contributors":contributors,
                      "method":"fixed 50/50 LLM votes and ML probabilities",
                      "llm_weight":LLM_WEIGHT}
    return {"predictions":forecasts,"statuses":metadata}
