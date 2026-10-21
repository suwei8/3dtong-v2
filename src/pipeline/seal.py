"""Verify sealed forecasts were committed exactly once to non-shallow Git history.

This detects post-hoc edits within the available Git history, but does not
claim to be a cryptographic timestamping authority or prevent force-pushes.
"""
import argparse
import json
import subprocess
from datetime import datetime,timezone
from pathlib import Path


def _git(root,*args):
    done=subprocess.run(["git","-C",str(root),*args],capture_output=True,
                        text=True,check=False,timeout=20)
    if done.returncode:
        raise ValueError("repository history unavailable")
    return done.stdout.strip()


def verify_seals(repo_root=".", relative_directory="predictions/live/runs",
                 expected_type="prospective-next-issue"):
    root=Path(repo_root).resolve()
    if _git(root,"rev-parse","--is-shallow-repository")!="false":
        raise ValueError("full Git history required; checkout with fetch-depth: 0")
    folder=(root/relative_directory).resolve()
    if not folder.is_relative_to(root) or not folder.is_dir():
        raise ValueError("missing or out-of-repository forecast directory")
    checked=[]
    for file in sorted(folder.glob("*.json")):
        relative=file.relative_to(root).as_posix()
        if _git(root,"status","--porcelain","--",relative):
            raise ValueError("uncommitted forecast modification: "+relative)
        lines=_git(root,"log","--format=%H%x09%cI","--",relative).splitlines()
        if len(lines)!=1:
            raise ValueError("forecast must have exactly one creation-only commit: "+relative)
        commit,timestamp=lines[0].split("\t",1)
        frozen=json.loads(file.read_text(encoding="utf-8"))
        if frozen.get("target_issue")!=file.stem or frozen.get("type")!=expected_type:
            raise ValueError("forecast target mismatch: "+relative)
        time=datetime.fromisoformat(frozen["generated_at_utc"].replace("Z","+00:00"))
        if time.tzinfo is None:
            raise ValueError("forecast time must include timezone: "+relative)
        published=datetime.fromisoformat(timestamp.replace("Z","+00:00"))
        lag=(published.astimezone(timezone.utc)-time.astimezone(timezone.utc)).total_seconds()
        if not -300<=lag<=7200:
            raise ValueError("forecast's generated timestamp differs from publication time: "+relative)
        parent_contents=subprocess.run(
            ["git","-C",str(root),"cat-file","-e",commit+"^:"+relative],
            capture_output=True,check=False,timeout=20
        )
        if parent_contents.returncode==0:
            raise ValueError("forecast already existed in commit parent: "+relative)
        checked.append({"issue":file.stem,"git_commit":commit,"committed_at_utc":published.isoformat()})
    print("Verified original immutable forecast records:",len(checked))
    return checked


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo",default=".")
    parser.add_argument("--forecasts",default="predictions/live/runs")
    parser.add_argument("--type",default="prospective-next-issue")
    args=parser.parse_args()
    verify_seals(args.repo,args.forecasts,args.type)


if __name__=="__main__":
    main()
