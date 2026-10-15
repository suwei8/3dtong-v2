"""Check all 9 anonymous OpenCode candidates against entirely synthetic statistics.

This is an availability probe, NOT a predictive performance benchmark.
Results are frozen per workflow run but may change at any moment.
"""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from src.models.llm.opencode_free import load_models,predict_model


def run(out="reports",timeout=None):
    models,per_model_timeout=load_models()
    if timeout is not None:
        if not 5<=timeout<=120:
            raise ValueError("invalid timeout")
        per_model_timeout=timeout
    synthetic={
        "as_of_issue":"SYNTHETIC-TEST-NOT-REAL",
        "draws_observed":300,
        "presence_counts":{
            "10":{str(d):[2,3,2,3,3,2,3,2,3,3][d] for d in range(10)},
            "30":{str(d):[7,9,8,8,10,7,10,6,8,10][d] for d in range(10)},
            "100":{str(d):[26,29,28,30,27,28,29,27,29,27][d] for d in range(10)}},
        "missing_streak":{str(d):d%5 for d in range(10)}
    }
    summary=json.dumps(synthetic,separators=(",",":"),sort_keys=True)
    entries=[]
    for index,model in enumerate(models,1):
        result=predict_model(summary,model,timeout=per_model_timeout)
        item={"model":model,"status":result["status"]}
        if "reason" in result:
            item["reason"]=result["reason"]
        if result["status"]=="ok":
            item["synthetic_response_digits"]=result["digits"]
        entries.append(item)
        print(f'{index}/{len(models)} {model}: {item["status"]} {item.get("reason","")}',flush=True)
    info={"schema":1,"kind":"anonymous-cli-availability-only",
          "tested_at_utc":datetime.now(timezone.utc).isoformat(),
          "synthetic_data_only":True,"login_required_by_this_test":False,
          "timeout_seconds":per_model_timeout,"models":entries}
    folder=Path(out)
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"opencode-availability.json").write_text(
        json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=["# OpenCode 匿名免费模型可用性实测","",
        f'时间（UTC）：{info["tested_at_utc"]}',
        "测试环境：GitHub Actions 全新 Ubuntu runner；**未设置任何 OpenCode 登录凭证**。",
        "以下仅表示当次合成数据请求能否成功，并非预测能力、长期免费承诺或实际开奖号码。","",
        "| 免费模型 | 可用状态 | 备注 |","|---|---|---|"]
    for item in entries:
        md.append(f'| '+item["model"]+" | "+("可调用" if item["status"]=="ok" else "跳过/失败")+
                  " | "+item.get("reason","JSON校验通过")+" |")
    md.extend(["","实际预测仅允许成功的合法模型输出加入当期封存结果。",
               "若免费模型配额、匿名访问权限或名字变动，下次运行可能不同。"])
    (folder/"opencode-availability.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    return info


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="reports")
    p.add_argument("--timeout",type=int,default=35)
    args=p.parse_args()
    run(out=args.out,timeout=args.timeout)
