"""Chronological model arena: train on past, select on pre-cutoff validation only."""
import numpy as np
from src.features.builder import build_dataset,feature_vector,WARMUP
from src.models.base import top3,accuracy
from src.models.xgboost_model import XGBoostPredictor
from src.models.lightgbm_model import LightGBMPredictor
from src.models.catboost_model import CatBoostPredictor
from src.models.ensemble import mean_proba
from src.models.dtong_model import rule_top3

MODELS=(XGBoostPredictor,LightGBMPredictor,CatBoostPredictor)
RANDOM_THEORY=1-.7**3

def train_all(history,validation_size=800):
    X,Y=build_dataset(history)
    cutoff=len(X)-validation_size
    if cutoff<500:
        raise ValueError("too little training history")
    scores={}
    trained={}
    for kind in MODELS:
        model=kind().fit(X[:cutoff],Y[:cutoff])
        trained[kind.name]=model
        p=model.predict_proba(X[cutoff:])
        scores[kind.name]={"validation_hit_rate":round(accuracy(p,Y[cutoff:]),6),
                           "validation_n":validation_size}
    ensemble=mean_proba({name:m.predict_proba(X[cutoff:]) for name,m in trained.items()})
    scores["ensemble"]={"validation_hit_rate":round(accuracy(ensemble,Y[cutoff:]),6),
                         "validation_n":validation_size}
    rules=[rule_top3(history[i-1]["KaiJiang"]) for i in range(WARMUP+cutoff,len(history))]
    rule_hits=sum(bool(set(pred)&{d for d,v in enumerate(label) if v})
                  for pred,label in zip(rules,Y[cutoff:]))
    scores["dtong-main10"]={"validation_hit_rate":round(rule_hits/validation_size,6),
                             "validation_n":validation_size}
    # baseline is a competitor, not an assumed model advantage.
    freq_predictions=[]
    for i in range(WARMUP+cutoff,len(history)):
        p=feature_vector(history[:i])
        freq_predictions.append(top3(p[10:20]))
    base_hits=sum(bool(set(pred)&{d for d,v in enumerate(label) if v})
                  for pred,label in zip(freq_predictions,Y[cutoff:]))
    scores["frequency-30"]={"validation_hit_rate":round(base_hits/validation_size,6),
                            "validation_n":validation_size}
    scores["random-theory"]={"validation_hit_rate":RANDOM_THEORY,"validation_n":0,
                              "note":"iid uniform mathematical baseline"}
    # Refit only after validation is frozen. Withheld dates have not been read.
    models={kind.name:kind().fit(X,Y) for kind in MODELS}
    current=feature_vector(history).reshape(1,-1)
    probabilities={name:model.predict_proba(current)[0] for name,model in models.items()}
    probabilities["ensemble"]=mean_proba(probabilities)
    # One-step models cannot honestly forecast ten-step transitions without true draws.
    # Thus each horizon uses the SAME fixed as-of-cutoff information.
    predictions={name:top3(prob) for name,prob in probabilities.items()}
    predictions["dtong-main10"]=rule_top3(history[-1]["KaiJiang"])
    predictions["frequency-30"]=top3(current[0,10:20])
    champion=max([k for k in scores if k!="random-theory"],
                 key=lambda k:(scores[k]["validation_hit_rate"],k))
    return {"scores":scores,"predictions":predictions,
            "champion_validation_only":champion,
            "probabilities":{name:[round(float(v),5) for v in prob]
                              for name,prob in probabilities.items()}}
