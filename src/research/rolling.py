"""Independent chronological, development-only rolling experiment.

The final holdout observations are excluded from feature construction,
training, tuning, scoring and reporting. No real data is included in CI tests.
"""
import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from sklearn.linear_model import Ridge
from src.data.loader import load_history
from src.data.validator import validate_rows
from src.evaluation.control import control_digits
from src.features.builder import WARMUP,build_dataset
from src.models.base import top3

FEATURE_GROUPS={
    "frequency":tuple(range(0,30)),
    "omission":tuple(range(30,40)),
    "position":tuple(range(40,70)),
    "previous":tuple(range(70,75)),
}
ALL_COLUMNS=tuple(range(75))
VARIANTS={
    "full":ALL_COLUMNS,
    "without_frequency":tuple(i for i in ALL_COLUMNS if i not in FEATURE_GROUPS["frequency"]),
    "without_omission":tuple(i for i in ALL_COLUMNS if i not in FEATURE_GROUPS["omission"]),
    "without_position":tuple(i for i in ALL_COLUMNS if i not in FEATURE_GROUPS["position"]),
    "without_previous":tuple(i for i in ALL_COLUMNS if i not in FEATURE_GROUPS["previous"]),
    "frequency_only":FEATURE_GROUPS["frequency"],
}
BASELINES=("frequency-30","sha256-random-control")


@dataclass(frozen=True)
class Config:
    holdout_size:int=200
    development_rounds:int=120
    refit_interval:int=20
    min_training_rows:int=500
    ridge_alpha:float=25.0


def _validate(history,cfg):
    validate_rows(history)
    if any(int(a["Issue"])>=int(b["Issue"]) for a,b in zip(history,history[1:])):
        raise ValueError("history must be oldest-first with strictly increasing issues")
    for key in ("holdout_size","development_rounds","refit_interval","min_training_rows"):
        value=getattr(cfg,key)
        if type(value) is not int or value<1:
            raise ValueError(key+" must be a positive integer")
    if cfg.min_training_rows<30:
        raise ValueError("min_training_rows must be >=30")
    if type(cfg.ridge_alpha) not in (int,float) or not math.isfinite(cfg.ridge_alpha) or cfg.ridge_alpha<=0:
        raise ValueError("ridge_alpha must be finite and positive")
    if len(history)<cfg.holdout_size+cfg.development_rounds+cfg.min_training_rows+WARMUP:
        raise ValueError("not enough history after reserving the entire untouched holdout")


def available_production_models():
    """Opt-in: reuse unchanged live estimator implementations for development study."""
    from src.pipeline.train import MODELS
    return {kind.name:kind for kind in MODELS}


def walk_forward(history,config=None,additional_models=None):
    """Diagnostic per-period records stay IN MEMORY; publish only aggregate()."""
    cfg=config or Config()
    _validate(history,cfg)
    dev=history[:-cfg.holdout_size]
    start=len(dev)-cfg.development_rounds
    X,Y=build_dataset(dev)
    if X.shape[1]!=75 or Y.shape[1]!=10:
        raise ValueError("feature layout changed; register a new ablation mapping")
    if start-WARMUP<cfg.min_training_rows:
        raise ValueError("insufficient training prefix")
    extra=additional_models if additional_models is not None else {}
    if not isinstance(extra,dict) or any(
        not isinstance(name,str) or not name or name in (*VARIANTS,*BASELINES)
        or not callable(factory) for name,factory in extra.items()
    ):
        raise ValueError("additional models must have unique names and callable factories")
    hits={name:[] for name in (*VARIANTS,*BASELINES,*extra)}
    trace=[]
    for first in range(start,len(dev),cfg.refit_interval):
        stop=min(len(dev),first+cfg.refit_interval)
        fit_end=first-WARMUP
        window=slice(first-WARMUP,stop-WARMUP)
        fitted={}
        for name,cols in VARIANTS.items():
            model=Ridge(alpha=cfg.ridge_alpha,solver="lsqr")
            model.fit(X[:fit_end,cols],Y[:fit_end])
            scores=model.predict(X[window,:][:,cols])
            fitted[name]=[top3(row) for row in scores]
        for name,factory in extra.items():
            # Exact production model class and parameters, but exploratory-only fit.
            estimator=factory().fit(X[:fit_end,:],Y[:fit_end])
            rankings=estimator.predict_proba(X[window,:])
            if rankings.shape!=(stop-first,10):
                raise ValueError("additional model must return one ten-digit score vector per issue")
            fitted[name]=[top3(row) for row in rankings]
        for offset,i in enumerate(range(first,stop)):
            picks={name:fitted[name][offset] for name in (*VARIANTS,*extra)}
            picks["frequency-30"]=top3(X[i-WARMUP,10:20])
            picks["sha256-random-control"]=control_digits(dev[i-1]["Issue"],dev[i]["Issue"])
            label=Y[i-WARMUP]
            vote_hits={name:bool(any(label[d] for d in digits)) for name,digits in picks.items()}
            for name,good in vote_hits.items():
                hits[name].append(good)
            trace.append({
                "issue":dev[i]["Issue"],
                "trained_through":dev[first-1]["Issue"],
                "votes":picks,
                "hits":vote_hits,
            })
    return {"config":cfg,"hits":hits,"trace":trace,"additional_models":list(extra)}


def _wilson(hits,n):
    p=hits/n
    z=1.96
    den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    delta=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(max(0.,centre-delta),6),round(min(1.,centre+delta),6)]


def aggregate(experiment):
    cfg=experiment["config"]
    ref=experiment["hits"]["full"]
    variants={}
    for name,values in experiment["hits"].items():
        n=len(values)
        good=sum(values)
        beat=sum(x and not y for x,y in zip(values,ref))
        lose=sum(y and not x for x,y in zip(values,ref))
        variants[name]={
            "hits":good,"samples":n,"rate":round(good/n,6),
            "wilson_95":_wilson(good,n),
            "paired_wins_vs_full":beat,
            "paired_losses_vs_full":lose,
            "paired_net_vs_full":beat-lose,
        }
    return {
        "schema":1,"kind":"exploratory-development-only",
        "model":"multi-output Ridge ablation plus optional unmodified production estimators",
        "additional_exploratory_models":experiment["additional_models"],
        "random_iid_theory":0.657,
        "config":{
            "holdout_size":cfg.holdout_size,
            "development_rounds":cfg.development_rounds,
            "refit_interval":cfg.refit_interval,
            "min_training_rows":cfg.min_training_rows,
            "ridge_alpha":cfg.ridge_alpha,
        },
        "feature_groups":{name:list(cols) for name,cols in FEATURE_GROUPS.items()},
        "variants":variants,
        "safety":{
            "holdout_used_in_training_or_scoring":False,
            "raw_draws_or_period_votes_in_report":False,
            "production_models_modified":False,
        },
        "warning":"Exploratory comparisons are correlated and vulnerable to overfitting; do not claim prediction advantage or tune on the held-out block.",
    }


def publish(experiment,output_directory):
    """Only publish aggregated metrics, never trace, labels or individual votes."""
    summary=aggregate(experiment)
    folder=Path(output_directory)
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"rolling-ablation.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    cfg=experiment["config"]
    lines=[
        "# 历史滚动回测与特征消融研究（探索性）","",
        "与每日事前预测及200期预注册研究**完全独立**；最后200期隔离数据不参与本次训练、分析或评分。",
        f"开发区测试：{cfg.development_rounds}期；每{cfg.refit_interval}期按历史重新训练；保留区：{cfg.holdout_size}期。",
        "消融使用 Ridge 多输出排名研究模型；如有额外模型，则使用其现有实现进行相同期号的滚动评估（仍非事前实战）。",
        "",
        "| 实验方案 | 命中 | 命中率 | 95% Wilson区间 | 相对全量特征的同期开奖净胜期数 |",
        "|---|---:|---:|---|---:|",
    ]
    for name,row in summary["variants"].items():
        lo,hi=row["wilson_95"]
        lines.append(f'| {name} | {row["hits"]}/{row["samples"]} | {row["rate"]*100:.2f}% | '
                     f'{lo*100:.1f}%–{hi*100:.1f}% | {row["paired_net_vs_full"]:+d} |')
    lines+=["","理论随机对照基准：65.7%（iid均匀假设）。",
            "该结果属探索性多重比较，不能据此宣称提高命中率，亦不能自动上线。",
            "公开文件不包含逐期开奖、逐期候选数字或私有源数据。",""]
    (folder/"rolling-ablation.md").write_text("\n".join(lines),encoding="utf-8")
    # Paired tests are descriptive because the pair was chosen AFTER inspecting
    # the development summary. Never use these results to unlock the holdout.
    if "xgboost" in experiment["hits"]:
        from src.research.paired import analyze_study, render_markdown
        paired=analyze_study(experiment)
        (folder/"rolling-paired.json").write_text(
            json.dumps(paired,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (folder/"rolling-paired.md").write_text(
            render_markdown(paired),encoding="utf-8")
    else:
        # An optional model not participating is not a negative vote.
        # Do not invent matched outcomes or mislabel the report as XGBoost.
        for stale in ("rolling-paired.json","rolling-paired.md"):
            (folder/stale).unlink(missing_ok=True)
    return summary


def main():
    p=argparse.ArgumentParser(description="Isolated historical feature ablation, never live forecasting")
    p.add_argument("--data",required=True,help="path to authorized private historical CSV")
    p.add_argument("--out",default="reports/experimental")
    p.add_argument("--holdout",type=int,default=200)
    p.add_argument("--rounds",type=int,default=120)
    p.add_argument("--refit-every",type=int,default=20)
    p.add_argument("--min-train",type=int,default=500)
    p.add_argument("--alpha",type=float,default=25.)
    p.add_argument("--include-current-models",action="store_true",
                   help="Also refit existing XGBoost/LightGBM/CatBoost on identical development issues (slow)")
    args=p.parse_args()
    cfg=Config(args.holdout,args.rounds,args.refit_every,args.min_train,args.alpha)
    factories=available_production_models() if args.include_current_models else None
    report=publish(walk_forward(load_history(args.data),cfg,additional_models=factories),args.out)
    print(f"Development-only rolling experiment: {report['config']['development_rounds']} rounds. Holdout excluded.")


if __name__=="__main__":
    main()
