"""Fixed-window, pre-registered prospective hypothesis tests.

Do not repeatedly test incomplete windows. Exactly the FIRST 200 valid
post-registration forecasts for each specified arm form its one-time test.
The 17-model Bonferroni factor was registered before their future outcomes.
"""
import json
import math
from pathlib import Path

REGISTRY=Path(__file__).resolve().parents[2]/"configs"/"research_protocol.json"


def exact_binomial_upper_tail(hits, n, null_p):
    """P(Binomial(n,p)>=hits), stable for moderate and large n."""
    if (type(hits) is not int or type(n) is not int or n<0 or not 0<=hits<=n
            or type(null_p) not in (float,int) or not 0<float(null_p)<1):
        raise ValueError("invalid binomial parameters")
    if hits==0:
        return 1.0
    # log-gamma supports n beyond factorial integer/float limits.
    p=float(null_p)
    log_p, log_q=math.log(p),math.log1p(-p)
    return min(1.0,math.fsum(
        math.exp(math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
                 +k*log_p+(n-k)*log_q)
        for k in range(hits,n+1)
    ))


def load_protocol(path=REGISTRY):
    protocol=json.loads(Path(path).read_text(encoding="utf-8"))
    if protocol.get("schema")!=1:
        raise ValueError("unknown protocol version")
    models=protocol["planned_models"]
    if not isinstance(models,list) or len(models)!=len(set(models)) or not models:
        raise ValueError("invalid registered model family")
    if protocol["sample_size_per_registered_model"]<1:
        raise ValueError("invalid registration sample target")
    return protocol


def analyze_scored_frozen_issues(completed, protocol=None):
    """Only scored FORECASTS after registered start, never retrospective holdout.

    completed: [{target_issue:'...',scores:{model:True/False,...}}]
    Repeated issue IDs are rejected. No target outcome digits are needed.
    """
    rules=protocol or load_protocol()
    names=rules["planned_models"]
    start=rules["start_issue"]
    horizon=rules["sample_size_per_registered_model"]
    p0=rules["null_hit_probability"]
    alpha=rules["one_sided_alpha"]
    control=rules["observational_control"]
    seen=set()
    ordered=[]
    for issue in sorted(completed,key=lambda v:v["target_issue"]):
        target=issue["target_issue"]
        if target in seen:
            raise ValueError("same completed issue counted twice")
        seen.add(target)
        if target<start:
            continue
        if not isinstance(issue.get("scores"),dict):
            raise ValueError("missing scored votes")
        if any(type(v) is not bool for v in issue["scores"].values()):
            raise ValueError("scores must be boolean, not raw digits")
        ordered.append(issue)
    results={}
    for name in [*names,control]:
        hits=[issue["scores"][name] for issue in ordered if name in issue["scores"]]
        first=hits[:horizon]
        n=len(first)
        successes=sum(first)
        complete=(n==horizon)
        value=exact_binomial_upper_tail(successes,n,p0) if complete and name!=control else None
        corrected=min(1.0,value*len(names)) if value is not None else None
        results[name]={
            "first_horizon_valid_votes":n,
            "horizon":horizon,
            "hits_in_window":successes,
            "window_complete":complete,
            "hit_rate":round(successes/n,6) if n else None,
            "raw_p_one_sided":round(value,12) if value is not None else None,
            "bonferroni_p":round(corrected,12) if corrected is not None else None,
            "passes_bonferroni_threshold":corrected < alpha if corrected is not None else None,
            "is_observational_control":name==control,
        }
    return {
        "schema":1,
        "protocol_name":rules["name"],
        "start_issue":start,
        "completed_prospective_issues_in_scope":len(ordered),
        "fixed_valid_votes_per_model":horizon,
        "random_null_p":p0,
        "multiple_comparison_factor":len(names),
        "one_sided_alpha":alpha,
        "statistical_warning":"No early significance claims; requires independent uniform draws, immutable preregistration, and fixed first-200 valid votes. Different models may cover different issues. Rejection is not proof of profitable prediction.",
        "models":results
    }


def publish_research(completed, output_dir="reports", protocol=None):
    result=analyze_scored_frozen_issues(completed,protocol)
    dest=Path(output_dir)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"research.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# 3dtong-v2｜预注册统计研究",
        "",
        "固定评估方案："+result["protocol_name"],
        f'纳入注册起点之后的已评分期数：**{result["completed_prospective_issues_in_scope"]}**',
        f'检验起点期号：**{result["start_issue"]}**；每个模型首次 **{result["fixed_valid_votes_per_model"]}** 次真实合法事前预测构成一个固定窗口。',
        f'理论随机命中概率：**{result["random_null_p"]*100:.1f}%**；',
        f'单侧精确二项检验；多重比较 Bonferroni 校正：**{result["multiple_comparison_factor"]} 个模型**。',
        "",
        "**未达到200次有效预测的模型不计算p值，也不宣称优于随机。**",
        "",
        "| 已注册模型 | 固定窗口进度 | 命中率（窗口内） | Bonferroni p |",
        "|---|---:|---:|---:|"
    ]
    for name,item in result["models"].items():
        rate=f'{item["hit_rate"]*100:.1f}%' if item["hit_rate"] is not None else "—"
        p=f'{item["bonferroni_p"]:.6g}' if item["bonferroni_p"] is not None else "待满200次"
        lines.append(f'| {name} | {item["first_horizon_valid_votes"]}/{item["horizon"]} | {rate} | {p} |')
    lines.extend([
        "",
        "**注意：** 固定评估样本可能存在模型调用失败/遗漏而分布在不同期号；",
        "这里的检验只针对理想独立随机模型，不构成模型之间两两优劣或收益性证明。",
        "不同于持续更新的实战命中率，这个协议不会在前200次完成前不断试探显著性。",
        "开奖码与私有训练数据不包含在本报告。",
        ""
    ])
    (dest/"research.md").write_text("\n".join(lines),encoding="utf-8")
    return result
