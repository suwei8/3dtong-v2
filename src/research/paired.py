"""Exploratory same-issue comparisons; aggregate only, never read private labels.

Exact McNemar conditions on discordant paired outcomes. A circular block
bootstrap gives a descriptive uncertainty band for the matched hit-rate gap,
allowing short-range time dependence. Neither corrects selection after trying
many model variants; do not treat these p-values as confirmatory evidence.
"""
import math
from random import Random


def exact_mcnemar_two_sided(candidate_only,baseline_only):
    if (type(candidate_only) is not int or type(baseline_only) is not int
            or min(candidate_only,baseline_only)<0):
        raise ValueError("discordant counts must be nonnegative integers")
    discordant=candidate_only+baseline_only
    if discordant==0:
        return 1.0
    extreme=min(candidate_only,baseline_only)
    # Integer arithmetic prevents underflow/overflow in the common n<=2000 use.
    outcomes=sum(math.comb(discordant,k) for k in range(extreme+1))
    return min(1.0,2.0*outcomes/(2**discordant))


def paired_comparison(candidate,baseline,block_length=10,replications=4000,
                      seed=20261021):
    if (not isinstance(candidate,(list,tuple)) or not isinstance(baseline,(list,tuple))
            or not candidate or len(candidate)!=len(baseline)
            or any(type(a) is not bool or type(b) is not bool
                   for a,b in zip(candidate,baseline))):
        raise ValueError("comparison requires equal nonempty lists of boolean outcomes")
    if (type(block_length) is not int or not 1<=block_length<=len(candidate)
            or type(replications) is not int or not 500<=replications<=100000
            or type(seed) is not int):
        raise ValueError("invalid block-bootstrap settings")
    n=len(candidate)
    both=sum(a and b for a,b in zip(candidate,baseline))
    only_candidate=sum(a and not b for a,b in zip(candidate,baseline))
    only_baseline=sum(b and not a for a,b in zip(candidate,baseline))
    neither=n-both-only_candidate-only_baseline
    delta=[int(a)-int(b) for a,b in zip(candidate,baseline)]
    rng=Random(seed)
    estimates=[]
    for _ in range(replications):
        total=0
        generated=0
        while generated<n:
            start=rng.randrange(n)
            take=min(block_length,n-generated)
            total+=sum(delta[(start+j)%n] for j in range(take))
            generated+=take
        estimates.append(total/n)
    estimates.sort()
    lo=estimates[int((replications-1)*0.025)]
    hi=estimates[int((replications-1)*0.975)]
    return {
        "samples":n,
        "both_hit":both,
        "candidate_only_hit":only_candidate,
        "baseline_only_hit":only_baseline,
        "both_miss":neither,
        "candidate_hits":both+only_candidate,
        "baseline_hits":both+only_baseline,
        "candidate_minus_baseline_percentage_points":round(100*(only_candidate-only_baseline)/n,4),
        "discordant_pairs":only_candidate+only_baseline,
        "mcnemar_two_sided_p_exploratory":round(
            exact_mcnemar_two_sided(only_candidate,only_baseline),8),
        "paired_circular_block_bootstrap_95_gap_pp":[round(100*lo,4),round(100*hi,4)],
        "bootstrap_settings":{"block_length":block_length,
                              "replications":replications,"seed":seed},
        "confirmatory":False,
    }


def analyze_study(study):
    data=study["hits"]
    if "xgboost" not in data or "frequency-30" not in data:
        raise ValueError("paired stage requires frozen XGBoost and frequency-30 votes")
    # The comparison is exploratory because the model pair was chosen after
    # reviewing the previous development summary. Do not promote based on this.
    comparisons={}
    for candidate,baseline in (
        ("xgboost","frequency-30"),
        ("xgboost","sha256-random-control"),
        ("without_frequency","full"),
    ):
        if candidate not in data or baseline not in data:
            raise ValueError(f"missing actual paired model: {candidate}/{baseline}")
        comparisons[candidate+"_vs_"+baseline]={
            "candidate":candidate,
            "baseline":baseline,
            **paired_comparison(data[candidate],data[baseline]),
        }
    return {
        "schema":1,
        "kind":"post-selection-exploratory-paired-comparison",
        "historical_source":"previously chosen fixed private history snapshot",
        "comparisons":comparisons,
        "holdout_evaluated":False,
        "production_modified":False,
        "candidate_policy":"No holdout unlock or live model promotion based on the exploratory pairwise p-values alone.",
        "warning":"Compared candidates were selected after looking at developmental leaderboard; unadjusted McNemar p-values and block-bootstrap intervals are descriptive only. Small samples and multiple comparisons limit conclusions.",
    }


def render_markdown(report):
    titles={
        "xgboost_vs_frequency-30":"XGBoost 对比30期频率",
        "xgboost_vs_sha256-random-control":"XGBoost 对比伪随机对照",
        "without_frequency_vs_full":"移除频率特征的 Ridge 对比完整特征 Ridge",
    }
    lines=[
        "# 同期开奖配对检验（探索性）","",
        "使用已锁定的120期开发样本及现有模型预测记录，每期一对一比较，保留最后200期作隔离区。",
        "**这不是独立确认性检验。** 这几组对比是在此前看过开发集排行榜后选择的；因此不能根据本报告 p 值判断预测模型已取得统计意义上的优势。",
        "",
        "| 对比 | 样本期数 | 仅前者命中 | 仅后者命中 | 双方都命中 | 双方都未命中 | 命中率差（百分点） | 精确McNemar双侧p（探索性） | 区块Bootstrap差值95%区间（百分点） |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name,item in report["comparisons"].items():
        lo,hi=item["paired_circular_block_bootstrap_95_gap_pp"]
        lines.append(f'| {titles.get(name,name)} | {item["samples"]} | '
                     f'{item["candidate_only_hit"]} | {item["baseline_only_hit"]} | '
                     f'{item["both_hit"]} | {item["both_miss"]} | '
                     f'{item["candidate_minus_baseline_percentage_points"]:+.2f} | '
                     f'{item["mcnemar_two_sided_p_exploratory"]:.4f} | '
                     f'{lo:+.2f}～{hi:+.2f} |')
    lines.extend([
        "",
        "说明：精确McNemar检验只使用双方胜负不一致的期号；区块Bootstrap采用10期循环区块、4000次重抽样、固定随机种子20261021。",
        "这里不输出原始开奖号、单期开奖结果、预测数字或私有数据。",
        "",
        "## 阶段决定",
        "",
        "先保留现有算法，不解锁200期隔离区，也不将探索性 XGBoost 优势写入实战预测权重。",
        "如要进入一次性隔离验证，必须先提交明确冻结的评估协议并记录数据快照与测试门槛；不得因本次结果继续调整阈值或回测窗口。",
        "",
    ])
    return "\n".join(lines)
