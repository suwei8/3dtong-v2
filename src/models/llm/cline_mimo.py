"""Opt-in, fail-closed Cline CLI challenger. Never invent a successful model vote.

Cline requires a configured provider credential on the executing machine.
Use a minimal aggregated feature summary; do not pass full private CSV,
credentials, or a checkout containing private files to a coding agent.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path


class ClineMimoPredictor:
    name="cline-mimo"
    model="mimo-v2.6-flash"
    provider="cline"

    def build_prompt(self, summary):
        return (
          "You are one blinded contestant in a research benchmark. "
          "Return ONLY one JSON object exactly shaped as "
          "{\"digits\":[0,1,2]}, using three distinct integers from 0 to 9. "
          "Do not call tools, execute commands, read files or modify the environment. "
          "You are NOT guaranteed to outperform chance. "
          "Provided historical aggregate statistics (no upcoming results):\n"
          + summary
        )

    def predict(self,summary,executable="cline",cwd=None,timeout=90):
        if not shutil.which(executable):
            return {"model":self.name,"status":"skipped","reason":"cline CLI unavailable"}
        if cwd is None:
            raise ValueError("explicit isolated cwd required for untrusted CLI")
        cmd=[executable,"--json","--auto-approve","false","-P",self.provider,
             "-m",self.model,"--timeout",str(timeout),"-c",str(Path(cwd).resolve()),
             self.build_prompt(summary)]
        try:
            proc=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,
                                 timeout=timeout+15,check=False)
        except (subprocess.TimeoutExpired,OSError) as ex:
            return {"model":self.name,"status":"skipped","reason":type(ex).__name__}
        if proc.returncode:
            return {"model":self.name,"status":"skipped","reason":"provider/CLI execution failed"}
        texts=[]
        for line in proc.stdout.splitlines():
            try:
                obj=json.loads(line)
                if obj.get("type")=="run_result":
                    texts.append(obj.get("text",""))
            except (ValueError,AttributeError):
                continue
        if not texts:
            return {"model":self.name,"status":"skipped","reason":"missing run_result"}
        try:
            match=re.search(r"\{[^{}]*\"digits\"\s*:\s*\[[^\]]+\][^{}]*\}",texts[-1])
            item=json.loads(match.group()) if match else {}
            digits=item.get("digits")
            if (not isinstance(digits,list) or len(digits)!=3 or
                    len(set(digits))!=3 or any(type(d) is not int or not 0<=d<=9 for d in digits)):
                raise ValueError("invalid digit schema")
        except (ValueError,TypeError):
            return {"model":self.name,"status":"skipped","reason":"invalid output"}
        return {"model":self.name,"status":"ok","digits":digits}
