"""Kilo free-model runner. No login, keys, shell tools, or raw draw records.

The model list is user-supplied and volatile; only actual successful CLI
outputs are accepted. In a clean GitHub runner, unavailable models are SKIPPED.
"""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

DEFAULT_MODELS_PATH=Path(__file__).resolve().parents[3] / "configs" / "kilo_models.json"


def load_models(path=DEFAULT_MODELS_PATH):
    config=json.loads(Path(path).read_text(encoding="utf-8"))
    models=config["models"]
    if (not isinstance(models,list) or not models or len(models)>20 or
        any(not isinstance(m,str) or not m.startswith("kilo/") or
            len(m)>100 for m in models) or len(set(models))!=len(models)):
        raise ValueError("invalid Kilo model list")
    timeout=config.get("per_model_timeout_seconds",45)
    if type(timeout) is not int or not 5<=timeout<=120:
        raise ValueError("invalid model timeout")
    return models,timeout


def parse_json_events(stdout):
    """Official kilo run --format json emits line-delimited events with text parts."""
    texts=[]
    for line in stdout.splitlines():
        try:
            item=json.loads(line)
        except (ValueError,TypeError):
            continue
        if not isinstance(item,dict):
            continue
        if item.get("type")=="error":
            raise ValueError("Kilo reported error")
        part=item.get("part")
        if item.get("type")=="text" and isinstance(part,dict) and isinstance(part.get("text"),str):
            texts.append(part["text"])
    if not texts:
        raise ValueError("missing assistant text events")
    # Combine text events because the CLI may split output into multiple parts.
    final="".join(texts).strip()
    fence=chr(96)*3
    if final.startswith(fence+"json") and final.endswith(fence):
        final=final[7:-3].strip()
    elif final.startswith(fence) and final.endswith(fence):
        final=final[3:-3].strip()
    try:
        payload=json.loads(final)
    except (TypeError,ValueError) as exc:
        raise ValueError("non-JSON model response") from exc
    if not isinstance(payload,dict) or set(payload)!={"digits"}:
        raise ValueError("expected a JSON object containing only digits")
    digits=payload["digits"]
    if (not isinstance(digits,list) or len(digits)!=3 or
        any(type(d) is not int or not 0<=d<=9 for d in digits) or
        len(set(digits))!=3):
        raise ValueError("expected three distinct digits from 0 to 9")
    return digits


def _clean_env(work):
    # Do not send GITHUB_TOKEN, PINBLE_DATA_TOKEN, account keys, or private paths.
    keep=("PATH","LANG","LC_ALL","HTTP_PROXY","HTTPS_PROXY","NO_PROXY",
          "SSL_CERT_FILE","SSL_CERT_DIR")
    env={k:os.environ[k] for k in keep if k in os.environ}
    root=str(work)
    env.update({"HOME":root,"XDG_CONFIG_HOME":str(work/"config"),
                "XDG_DATA_HOME":str(work/"data"),
                "XDG_CACHE_HOME":str(work/"cache"),
                "XDG_STATE_HOME":str(work/"state")})
    return env


def classify_cli_failure(stdout, stderr):
    """Only a fixed safe category is returned: never raw gateway messages/tokens."""
    parts=[stdout or "",stderr or ""]
    for line in (stdout or "").splitlines():
        try:
            event=json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(event,dict) and event.get("type")=="error":
            # Gateway errors may be nested JSON, with a zero process exit code.
            parts.append(json.dumps(event.get("error",{}),ensure_ascii=True))
    msg="\n".join(parts).lower()
    if ("can only be used from within" in msg or
            "free tier can only" in msg):
        return "Kilo free-tier gateway tool/permission rejection"
    if ("freeusagelimiterror" in msg or "usage limit" in msg or
            "rate limit" in msg or "too many requests" in msg or
            "429" in msg or "quota" in msg or "insufficient credit" in msg or
            "insufficient balance" in msg):
        return "Kilo free-model rate limit (429), quota or credits"
    if "abusive traffic" in msg or "ip address" in msg and "blocked" in msg:
        return "Kilo gateway IP anti-abuse block"
    if ("deprecated" in msg or "retired" in msg or "discontinued" in msg):
        return "Kilo model ID retired or deprecated"
    if ("model not found" in msg or "unknown model" in msg or
            "model is unavailable" in msg or "model unavailable" in msg or
            "providermodelnotfounderror" in msg or "no-route" in msg or
            "404" in msg):
        return "Kilo model ID missing or unavailable (404)"
    if "401" in msg or "unauthorized" in msg or "invalid credential" in msg:
        return "Kilo gateway authorization rejection (401)"
    if "403" in msg or "forbidden" in msg:
        return "Kilo gateway forbidden (403); verify free-tier policy"
    if ("network" in msg or "not connected" in msg or
            "econnreset" in msg or "etimedout" in msg or "fetch failed" in msg):
        return "Kilo network/connection failure"
    if "provider" in msg and "error" in msg:
        return "Kilo provider error (unspecified)"
    return "Kilo CLI nonzero / provider response (unclassified)"


def predict_model(summary,model,executable="kilo",timeout=45):
    """Run one anonymous Kilo free contender in isolation.

    Requiring a clean workspace avoids exposing private source files.
    The Kilo permission policy requires confirmation for tools (with write, network and task tools denied); no approvals are supplied.
    """
    if not isinstance(summary,str) or len(summary)>15000:
        raise ValueError("summary must be a small aggregate string")
    approved,_=load_models()
    if model not in approved:
        raise ValueError("model is not in approved free-model list")
    if not shutil.which(executable):
        return {"model":model,"status":"skipped","reason":"Kilo CLI unavailable"}
    with tempfile.TemporaryDirectory(prefix="3dtong-kilo-") as temp:
        work=Path(temp)
        (work/"kilo.json").write_text(
            json.dumps({"$schema":"https://kilo.ai/config.json",
                        "share":"disabled",
                        "permission":{"*":"ask","edit":"deny",
                                      "webfetch":"deny","websearch":"deny",
                                      "task":"deny"}},sort_keys=True),
            encoding="utf-8")
        prompt=("Research contestant. Using ONLY the following aggregated historical digit counts, "
                "select three DISTINCT integers 0..9. Do not request tools or read files. "
                "Return strictly one JSON object with no Markdown or commentary: "
                '{"digits":[0,1,2]}' + "\n" + summary)
        cmd=[executable,"run","--format","json","--model",model,prompt]
        try:
            done=subprocess.run(cmd,cwd=work,env=_clean_env(work),capture_output=True,
                                text=True,timeout=timeout,check=False)
        except (subprocess.TimeoutExpired,OSError) as exc:
            return {"model":model,"status":"skipped","reason":type(exc).__name__}
        if done.returncode:
            return {"model":model,"status":"skipped",
                    "reason":classify_cli_failure(done.stdout,done.stderr)}
        try:
            digits=parse_json_events(done.stdout)
        except ValueError as exc:
            if str(exc)=="Kilo reported error":
                why=classify_cli_failure(done.stdout,done.stderr)
            else:
                why=str(exc)
            return {"model":model,"status":"skipped","reason":why}
        return {"model":model,"status":"ok","digits":digits}


def compete(history,models=None,timeout=None,budget_seconds=None,clock=None):
    """Run candidates under an overall wall-clock budget.

    Each success is an actual Kilo reply; all unattempted candidates are
    marked 'skipped' so a late Kilo model cannot hold the ML forecast hostage.
    The monotonic clock makes the budget robust to wall-clock adjustments.
    """
    from src.models.llm.contestant import summary_for_llm
    default,default_timeout=load_models()
    selected=default if models is None else models
    if not isinstance(selected,list) or any(m not in default for m in selected):
        raise ValueError("requested model IDs must be in approved free list")
    if len(selected)!=len(set(selected)):
        raise ValueError("duplicate Kilo candidate")
    ttl=default_timeout if timeout is None else timeout
    if type(ttl) is not int or ttl<5 or ttl>120:
        raise ValueError("per-model timeout must be 5..120 seconds")
    if budget_seconds is not None and (type(budget_seconds) not in (int,float)
                                        or not 0<=budget_seconds<=1800):
        raise ValueError("budget must be 0..1800 seconds")
    watch=clock or time.monotonic
    began=watch()
    summary=summary_for_llm(history)
    results={}
    for model in selected:
        if budget_seconds is None:
            effective=ttl
        else:
            remaining=budget_seconds-(watch()-began)
            if remaining<5:
                results[model]={"model":model,"status":"skipped",
                                "reason":"overall Kilo budget exhausted"}
                continue
            # Decimal seconds are accepted by subprocess timeout; leave
            # a short buffer for scheduling/serialization overhead.
            effective=min(ttl,max(5,remaining-1))
        try:
            result=predict_model(summary,model,timeout=effective)
        except (OSError,subprocess.SubprocessError) as exc:
            result={"model":model,"status":"skipped",
                    "reason":"Kilo invocation error: "+type(exc).__name__}
        results[model]=result
    return results
