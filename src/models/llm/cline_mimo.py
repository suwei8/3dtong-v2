"""Optional Cline CLI challenger. Free promotional models work through CLI, not REST."""
import json
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_MODEL="cline-free/mimo-v2.6-flash"

def parse_run_result(stdout):
    """Accept exactly the final structured JSON event from Cline NDJSON."""
    finals=[]
    for line in stdout.splitlines():
        try:
            event=json.loads(line)
        except (ValueError,TypeError):
            continue
        if isinstance(event,dict) and event.get("type")=="run_result" and isinstance(event.get("text"),str):
            finals.append(event["text"].strip())
    if not finals:
        raise ValueError("no final run_result")
    final=finals[-1]
    fence=chr(96)*3
    if final.startswith(fence+"json") and final.endswith(fence):
        final=final[len(fence+"json"):-len(fence)].strip()
    elif final.startswith(fence) and final.endswith(fence):
        final=final[len(fence):-len(fence)].strip()
    try:
        obj=json.loads(final)
    except (ValueError,TypeError) as exc:
        raise ValueError("non-JSON final answer") from exc
    if not isinstance(obj,dict) or set(obj)!={"digits"}:
        raise ValueError("expected only digits field")
    digits=obj["digits"]
    if (not isinstance(digits,list) or len(digits)!=3
        or any(type(d) is not int or not 0<=d<=9 for d in digits)
        or len(set(digits))!=3):
        raise ValueError("invalid three distinct digits")
    return digits

class ClineMimoPredictor:
    name="cline-mimo"
    provider="cline"
    def __init__(self,model=DEFAULT_MODEL):
        self.model=model

    def build_prompt(self,summary):
        return (
            "You are a blinded contestant in a numeric research benchmark. "
            "Do not access files, call tools, execute commands or request approvals. "
            "Use ONLY the supplied aggregate statistics; they exclude future draws. "
            "Reply with exactly one JSON object and no other text: "
            '{"digits":[0,1,2]}. '
            "All digits must be distinct integers between 0 and 9. "
            "No prediction is guaranteed to outperform chance.\nAggregates:\n"+summary
        )

    def predict(self,summary,executable="cline",cwd=None,timeout=90):
        if cwd is None or not Path(cwd).is_dir():
            raise ValueError("explicit isolated workspace required")
        if list(Path(cwd).iterdir()):
            raise ValueError("workspace must be empty")
        if not shutil.which(executable):
            return {"model":self.name,"status":"skipped","reason":"CLI unavailable"}
        cmd=[executable,"--json","--auto-approve","false",
             "--provider",self.provider,"--model",self.model,
             "--timeout",str(timeout),"--cwd",str(Path(cwd).resolve()),
             self.build_prompt(summary)]
        # Pass Cline credential only; do not pass GitHub/private data tokens.
        allowed=("HOME","PATH","LANG","LC_ALL","XDG_CONFIG_HOME",
                 "XDG_DATA_HOME","XDG_RUNTIME_DIR","TMPDIR",
                 "HTTPS_PROXY","HTTP_PROXY","NO_PROXY","CLINE_API_KEY")
        env={k:os.environ[k] for k in allowed if k in os.environ}
        try:
            proc=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,
                                text=True,timeout=timeout+15,check=False)
        except (subprocess.TimeoutExpired,OSError) as exc:
            return {"model":self.name,"status":"skipped","reason":type(exc).__name__}
        if proc.returncode:
            return {"model":self.name,"status":"skipped","reason":"CLI or authentication failed"}
        try:
            digits=parse_run_result(proc.stdout)
        except ValueError as exc:
            return {"model":self.name,"status":"skipped","reason":str(exc)}
        return {"model":self.name,"status":"ok","digits":digits,"model_id":self.model}
