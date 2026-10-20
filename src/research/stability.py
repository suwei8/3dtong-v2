"""Exploratory time-slice stability study on EXISTING frozen development outcomes.

All figures are aggregates over non-overlapping refit intervals. No new model
training, held-out draw inspection, individual issue ID or digit publication.
Never use these post-hoc metrics to promote a production model.
"""

PAIRS=(
    ("xgboost","frequency-30"),
    ("xgboost","sha256-random-control"),
    ("without_frequency","full"),
)
FOCUS=("xgboost","frequency-30","lightgbm","catboost",
       "sha256-random-control","without_frequency","full")


def analyze_stability(study):
    config=study["config"]
    outcomes=study["hits"]
    rounds=config.development_rounds
    size=config.refit_interval
    if (type(rounds) is not int or type(size) is not int
            or rounds<2 or size<1 or rounds%size!=0):
        raise ValueError("development periods must split into complete refit blocks")
    if (not isinstance(outcomes,dict) or not outcomes
            or any(len(values)!=rounds or any(type(v) is not bool for v in values)
                   for values in outcomes.values())):
        raise ValueError("all models must cover every development period with boolean hits")
    tracked=[name for name in FOCUS if name in outcomes]
    if "full" not in tracked or "frequency-30" not in tracked:
        raise ValueError("stability report requires original full and frequency baselines")
    blocks=[]
    for start in range(0,rounds,size):
        block={"block_index":len(blocks)+1,"sample_count":size,
               "model_hits":{name:sum(outcomes[name][start:start+size]) for name in tracked}}
        blocks.append(block)

    comparisons={}
    for name,reference in PAIRS:
        if name not in outcomes:
            continue  # unavailable optional model does NOT mean missing prediction.
        if reference not in outcomes:
            raise ValueError(f"missing comparison reference {reference}")
        details=[]
        for i,start in enumerate(range(0,rounds,size)):
            a=outcomes[name][start:start+size]
            b=outcomes[reference][start:start+size]
            candidate_only=sum(x and not y for x,y in zip(a,b))
            reference_only=sum(y and not x for x,y in zip(a,b))
            both=sum(x and y for x,y in zip(a,b))
            neither=size-candidate_only-reference_only-both
            details.append({
                "block_index":i+1,
                "candidate_hits":sum(a),
                "reference_hits":sum(b),
                "candidate_only":candidate_only,
                "reference_only":reference_only,
                "both_hit":both,
                "both_miss":neither,
                "net_hit_difference":candidate_only-reference_only,
                "hit_rate_gap_pp":round(100*(candidate_only-reference_only)/size,4),
            })
        nets=[x["net_hit_difference"] for x in details]
        comparisons[name+"_vs_"+reference]={
            "candidate":name,"baseline":reference,"segments":details,
            "better_segments":sum(x>0 for x in nets),
            "worse_segments":sum(x<0 for x in nets),
            "tied_segments":sum(x==0 for x in nets),
            "total_net_hits":sum(nets),
            "smallest_segment_gap_pp":min(x["hit_rate_gap_pp"] for x in details),
            "largest_segment_gap_pp":max(x["hit_rate_gap_pp"] for x in details),
            "dominates_each_segment":all(x>0 for x in nets),
        }
    return {
        "schema":1,
        "kind":"post-hoc-exploratory-time-stability",
        "source":"same pinned development snapshot as rolling-paired report",
        "development_rounds":rounds,
        "segment_size":size,
        "segment_count":len(blocks),
        "segment_definition":"chronological non-overlapping refit blocks",
        "blocks":blocks,
        "comparisons":comparisons,
        "holdout_evaluated":False,
        "raw_issues_draws_votes_published":False,
        "production_modified":False,
        "adoption_approved":False,
        "warning":"Selected after examining development leaderboard. Aggregate segment stability is descriptive and cannot establish predictive advantage; small samples and correlated outcomes.",
    }


def render_markdown(report):
    segments=report["blocks"]
    names=[*segments[0]["model_hits"]]
    rows=[
        "# 模型跨时间区间稳定性研究（探索性）","",
        f'使用已固定的同一份开发历史，将 **{report["development_rounds"]}期** 拆分为 '
        f'**{report["segment_count"]}段、每段{report["segment_size"]}期**。分段与原模型滚动重训边界保持一致。',
        "本报告没有重新选择任何期号或修改预测；最后200期隔离区未参与训练或评分。","",
        "## 各时间段命中次数","",
        "| 时间段（从早到晚） | "+ " | ".join(names) +" |",
        "|---:|"+ "|".join("---:" for _ in names) +"|",
    ]
    for block in segments:
        values=[f'{block["model_hits"][name]}/{block["sample_count"]}' for name in names]
        rows.append(f'| 第{block["block_index"]}段 | '+' | '.join(values)+' |')

    rows+=["","## 同一期配对差异在各时段的稳定性","",
           "| 对比 | 领先区段 | 落后区段 | 持平区段 | 全120期净多命中 | 最差区段差距 | 最好区段差距 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for item in report["comparisons"].values():
        name=f'{item["candidate"]} vs {item["baseline"]}'
        rows.append(
            f'| {name} | {item["better_segments"]} | '
            f'{item["worse_segments"]} | {item["tied_segments"]} | '
            f'{item["total_net_hits"]:+d} | {item["smallest_segment_gap_pp"]:+.1f}百分点 | '
            f'{item["largest_segment_gap_pp"]:+.1f}百分点 |'
        )
    rows+=["",
           "**解读原则：** 一个模型在总120期领先，不代表每个20期区段都领先。",
           "分段仅用于观察波动和集中性；不能把分段数当作独立试验，也不能根据分段挑选新的调参窗口。",
           "这些比较是在看过开发集结果后选择的，因此不是确认性显著性证据。",
           "本轮 **不允许自动解锁最后200期隔离验证，不修改生产模型或实战排行榜**。",
           "所有公开数据仅是分段命中总数，没有任何原始开奖号、期号、逐期预测或逐期标签。",""]
    return "\n".join(rows)
