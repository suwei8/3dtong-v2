"""Raw Kilo CLI diagnostics for anonymous free-model reachability.

predict_model() deliberately collapses provider failures into safe buckets;
this diagnostic keeps the raw error event fields (type/status/message/
retryAfterMs) and diffs the live `kilo models` catalogue against the
configured candidate list so a human can see WHY anonymous calls fail.

Synthetic prompt only; never touches private draw history. The raw gateway
text goes to reports/kilo-diagnose.json, which the diagnose workflow
uploads as an artifact and never commits to the repository.
"""
import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime,timezone
from pathlib import Path
from src.models.llm.kilo_free import _clean_env,classify_cli_failure,load_models

MODEL_LINE=re.compile(r"^[A-Za-z0-9_-]+/[A-Za-z0-9._~/:-]+$")
FREE_HINT=re.compile(r"free",re.IGNORECASE)
DIAG_PROMPT='Reply with exactly {"digits":[1,2,3]} and nothing else.'
MAX_TEXT=400


def cli_version(executable):
    try:
        done=subprocess.run([executable,"--version"],capture_output=True,text=True,timeout=30)
    except (subprocess.TimeoutExpired,OSError) as exc:
        return {"error":type(exc).__name__}
    line=((done.stdout or done.stderr).strip().splitlines() or [""])[0]
    return {"version":line.strip(),"exit_code":done.returncode}


def catalogue(executable,work,env,timeout=90):
    """Return every provider/model line the CLI lists for this anonymous HOME."""
    try:
        done=subprocess.run([executable,"models"],cwd=work,env=env,
                            capture_output=True,text=True,timeout=timeout)
    except (subprocess.TimeoutExpired,OSError) as exc:
        return {"listed":False,"error":type(exc).__name__,"models":[]}
    ids=sorted({line.strip() for line in done.stdout.splitlines()
                if MODEL_LINE.match(line.strip())})
    record={"listed":done.returncode==0,"models":ids}
    if done.returncode!=0:
        record["error"]=f"exit {done.returncode}"
    if done.stderr.strip():
        record["stderr_excerpt"]=done.stderr.strip()[:MAX_TEXT]
    return record


def _nested_error_type(error):
    """Unwrap the upstream JSON body embedded in provider error events."""
    response=error.get("response")
    if not isinstance(response,dict):
        return None
    body=response.get("body")
    if not isinstance(body,str):
        return None
    try:
        inner=json.loads(body)
    except ValueError:
        return None
    if isinstance(inner,dict) and isinstance(inner.get("error"),dict):
        return inner["error"].get("type")
    return None


def extract_error(stdout):
    """Last {"type":"error"} event wins; earlier step events are noise."""
    found=None
    for line in (stdout or "").splitlines():
        try:
            item=json.loads(line)
        except (ValueError,TypeError):
            continue
        if isinstance(item,dict) and item.get("type")=="error" and isinstance(item.get("error"),dict):
            found=item["error"]
    return found


def extract_reply_text(stdout,limit=MAX_TEXT):
    texts=[]
    for line in (stdout or "").splitlines():
        try:
            item=json.loads(line)
        except (ValueError,TypeError):
            continue
        if isinstance(item,dict) and item.get("type")=="text":
            part=item.get("part")
            if isinstance(part,dict) and isinstance(part.get("text"),str):
                texts.append(part["text"])
    return "".join(texts).strip()[:limit]


def probe(executable,model,work,env,timeout):
    """One anonymous `kilo run` with raw provider evidence retained."""
    started=time.monotonic()
    cmd=[executable,"run","--format","json","--model",model,DIAG_PROMPT]
    try:
        done=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"model":model,"status":"timeout","timeout_s":timeout}
    except OSError as exc:
        return {"model":model,"status":"spawn-error","error":type(exc).__name__}
    record={"model":model,"exit_code":done.returncode,
            "duration_s":round(time.monotonic()-started,2),
            "classification":classify_cli_failure(done.stdout,done.stderr)}
    error=extract_error(done.stdout)
    if error is not None:
        record["status"]="error"
        if error.get("type"):
            record["error_type"]=error["type"]
        nested=_nested_error_type(error)
        if nested:
            record["upstream_error_type"]=nested
        if error.get("status"):
            record["http_status"]=error["status"]
        if error.get("retryAfterMs"):
            record["retry_after_ms"]=error["retryAfterMs"]
            record["retry_after_hours"]=round(error["retryAfterMs"]/3_600_000,2)
        if error.get("message"):
            record["message"]=str(error["message"])[:MAX_TEXT]
        record["raw_error"]=json.dumps(error,ensure_ascii=False)[:600]
    else:
        text=extract_reply_text(done.stdout)
        record["status"]="ok" if done.returncode==0 and text else "error"
        if text:
            record["reply_excerpt"]=text
        else:
            record["message"]="no assistant text events"
    if done.stderr.strip():
        record["stderr_excerpt"]=done.stderr.strip()[:MAX_TEXT]
    return record


def build_report(executable,models,timeout,probe_discovered=True):
    info={"schema":1,"kind":"kilo-free-diagnostics",
          "tested_at_utc":datetime.now(timezone.utc).isoformat(),
          "synthetic_data_only":True,"anonymous_no_credentials":True,
          "cli":cli_version(executable),"timeout_seconds":timeout}
    if not shutil.which(executable):
        info["fatal"]="Kilo CLI not on PATH"
        info["results"]=[{"model":m,"status":"skipped","reason":"CLI unavailable"} for m in models]
        return info
    with tempfile.TemporaryDirectory(prefix="3dtong-kdiag-") as temp:
        work=Path(temp)
        def fresh_env(name):
            home=work/name
            home.mkdir()
            (home/"kilo.json").write_text(
                json.dumps({"$schema":"https://kilo.ai/config.json","share":"disabled",
                            "permission":{"*":"ask","edit":"deny","webfetch":"deny",
                                          "websearch":"deny","task":"deny"}},sort_keys=True),
                encoding="utf-8")
            return home,_clean_env(home)

        cat_home,cat_env=fresh_env("catalogue")
        cat=catalogue(executable,cat_home,cat_env)
        visible=set(cat["models"])
        configured=set(models)
        new_free=sorted(m for m in visible-configured
                        if m.startswith("kilo/") and FREE_HINT.search(m.rsplit("/",1)[-1]))
        info["catalogue"]={**cat,
            "configured_missing_from_listing":sorted(configured-visible),
            "visible_not_configured":new_free}
        targets=[(m,False) for m in models]
        if probe_discovered:
            targets+=[(m,True) for m in new_free]
        results=[]
        for index,(model,discovered) in enumerate(targets,1):
            home,env=fresh_env(f"probe-{index}")
            record=probe(executable,model,home,env,timeout)
            if discovered:
                record["discovered_in_catalogue"]=True
            record["in_catalogue_listing"]=model in visible
            results.append(record)
            print(f'{index}/{len(targets)} {model}: {record["status"]} '
                  f'{record.get("error_type","")} {record.get("classification","")}',flush=True)
        info["results"]=results
    ok=[r for r in info["results"] if r["status"]=="ok"]
    info["summary"]={"probed":len(info["results"]),"ok":len(ok),
                     "free_limit":sum(1 for r in info["results"]
                                      if r.get("error_type")=="provider.free-limit"),
                     "no_route":sum(1 for r in info["results"]
                                    if r.get("error_type")=="provider.no-route")}
    return info


def markdown(info):
    lines=["# Kilo 匿名免费模型诊断","",
           f'- 时间（UTC）：{info["tested_at_utc"]}',
           f'- CLI：`{info["cli"].get("version",info["cli"].get("error","?"))}`；未配置任何凭证（匿名）',
           f'- 探测 {info.get("summary",{}).get("probed",0)} 个模型：'
           f'成功 {info.get("summary",{}).get("ok",0)}，'
           f'免费额度耗尽 {info.get("summary",{}).get("free_limit",0)}，'
           f'路由不存在 {info.get("summary",{}).get("no_route",0)}',""]
    cat=info.get("catalogue",{})
    if cat.get("listed"):
        missing=cat.get("configured_missing_from_listing") or ["（无）"]
        new=cat.get("visible_not_configured") or ["（无）"]
        lines+=["## 实时目录对比","",
                "- 配置中但目录已移除："+", ".join(f"`{m}`" for m in missing),
                "- 目录新增免费模型："+", ".join(f"`{m}`" for m in new),""]
    lines+=["## 逐模型原始结果","",
            "| 模型 | 目录中 | 结果 | error.type | HTTP | 重试(小时) | 信息 |",
            "|---|---|---|---|---|---|---|"]
    for r in info.get("results",[]):
        catalog="是" if r.get("in_catalogue_listing") else "否"
        retry=r.get("retry_after_hours","—")
        detail=r.get("message") or r.get("reply_excerpt") or r.get("error","")
        detail=detail.replace("|","\\|")[:120]
        lines.append(f'| `{r["model"]}` | {catalog} | {r["status"]} | '
                     f'{r.get("error_type","—")} | {r.get("http_status","—")} | '
                     f'{retry} | {detail} |')
    return "\n".join(lines)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="reports/kilo-diagnose.json")
    p.add_argument("--timeout",type=int,default=60)
    p.add_argument("--executable",default="kilo")
    p.add_argument("--no-discovered",action="store_true",
                   help="only probe configured models, skip catalogue discoveries")
    args=p.parse_args()
    if not 5<=args.timeout<=300:
        raise ValueError("timeout must be 5..300 seconds")
    models,_=load_models()
    info=build_report(args.executable,models,args.timeout,
                      probe_discovered=not args.no_discovered)
    path=Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(markdown(info))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
