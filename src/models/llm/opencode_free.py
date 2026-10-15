"""OpenCode free-model runner. No login, keys, shell tools, or raw draw records.

The model list is user-supplied and volatile; only actual successful CLI
outputs are accepted. In a clean GitHub runner, unavailable models are SKIPPED.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_MODELS_PATH=Path(__file__).resolve().parents[3] / "configs" / "opencode_models.json"


def load_models(path=DEFAULT_MODELS_PATH):
    config=json.loads(Path(path).read_text(encoding="utf-8"))
    models=config["models"]
    if (not isinstance(models,list) or not models or len(models)>20 or
        any(not isinstance(m,str) or not m.startswith("opencode/") or
            len(m)>100 for m in models) or len(set(models))!=len(models)):
        raise ValueError("invalid OpenCode model list")
    timeout=config.get("per_model_timeout_seconds",45)
    if type(timeout) is not int or not 5<=timeout<=120:
        raise ValueError("invalid model timeout")
    return models,timeout


def parse_json_events(stdout):
    """Official opencode run --format json emits line-delimited events with text parts."""
    texts=[]
    for line in stdout.splitlines():
        try:
            item=json.loads(line)
        except (ValueError,TypeError):
            continue
        if not isinstance(item,dict):
            continue
        if item.get("type")=="error":
            raise ValueError("OpenCode reported error")
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


def predict_model(summary,model,executable="opencode",timeout=45):
    """Run one authenticated-or-anonymous OpenCode free contender in isolation.

    Requiring a clean workspace avoids exposing private source files.
    The OpenCode permission config denies ALL tools, including reading files.
    """
    if not isinstance(summary,str) or len(summary)>15000:
        raise ValueError("summary must be a small aggregate string")
    approved,_=load_models()
    if model not in approved:
        raise ValueError("model is not in approved free-model list")
    if not shutil.which(executable):
        return {"model":model,"status":"skipped","reason":"OpenCode CLI unavailable"}
    with tempfile.TemporaryDirectory(prefix="3dtong-opencode-") as temp:
        work=Path(temp)
        (work/"opencode.json").write_text(
            json.dumps({"$schema":"https://opencode.ai/config.json",
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
            # Never expose raw stdout/stderr; they may contain sensitive diagnostics.
            diagnostic=(done.stderr+"\n"+done.stdout).lower()
            if "invalid credential" in diagnostic or "unauthorized" in diagnostic:
                why="OpenCode gateway rejected anonymous credential"
            elif "can only be used from within opencode" in diagnostic:
                why="OpenCode free-tier agent permission gate rejected request"
            elif "model is unavailable" in diagnostic or "model unavailable" in diagnostic:
                why="free model currently unavailable"
            elif "model not found" in diagnostic or "unknown model" in diagnostic:
                why="model ID not supported by installed OpenCode"
            elif "rate limit" in diagnostic or "quota" in diagnostic:
                why="free model rate limit or quota"
            elif "not connected" in diagnostic or "network" in diagnostic:
                why="OpenCode network problem"
            else:
                why="CLI exit nonzero; inspect model availability"
            return {"model":model,"status":"skipped","reason":why}
        try:
            digits=parse_json_events(done.stdout)
        except ValueError as exc:
            return {"model":model,"status":"skipped","reason":str(exc)}
        return {"model":model,"status":"ok","digits":digits}


def compete(history,models=None,timeout=None):
    from src.models.llm.contestant import summary_for_llm
    default,default_timeout=load_models()
    selected=models or default
    ttl=default_timeout if timeout is None else timeout
    # Failures must not invent votes or break the classical model arena.
    summary=summary_for_llm(history)
    results={}
    for model in selected:
        results[model]=predict_model(summary,model,timeout=ttl)
    return results
