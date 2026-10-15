"""Freeze an honest next-issue forecast from a private, advancing result feed."""
import calendar
import csv
import hashlib
import re
from pathlib import Path
from .validator import validate_rows


def next_issue(issue):
    if not re.fullmatch(r"\d{7}", str(issue)):
        raise ValueError("invalid issue")
    year, sequence = int(issue[:4]), int(issue[4:])
    max_sequence = 366 if calendar.isleap(year) else 365
    if not 1 <= sequence <= max_sequence:
        raise ValueError("invalid issue sequence")
    return f"{year + 1}001" if sequence == max_sequence else f"{year}{sequence + 1:03d}"


def load_live_history(path):
    """Return known draws and target issue without using any pending outcome.

    A blank KaiJiang is allowed ONLY for the immediately next issue.
    """
    source=Path(path)
    raw=source.read_bytes()
    reader=csv.DictReader(raw.decode("utf-8-sig").splitlines())
    if not {"Issue","KaiJiang"}.issubset(reader.fieldnames or []):
        raise ValueError("missing Issue or KaiJiang column")
    complete=[]
    pending=[]
    seen=set()
    for row in reader:
        issue=str(row["Issue"]).strip()
        code=str(row["KaiJiang"] or "").strip()
        if not re.fullmatch(r"\d{7}", issue):
            raise ValueError("invalid issue "+issue)
        if issue in seen:
            raise ValueError("duplicate issue "+issue)
        seen.add(issue)
        if code == "":
            pending.append(issue)
        elif re.fullmatch(r"\d{3}",code):
            complete.append({"Issue":issue,"KaiJiang":code})
        else:
            raise ValueError("invalid draw code at "+issue)
    complete.sort(key=lambda item:int(item["Issue"]))
    validate_rows(complete)
    if len(complete)<1100:
        raise ValueError("insufficient history for 800-round validation")
    expected=next_issue(complete[-1]["Issue"])
    if pending and (len(pending)!=1 or pending[0]!=expected):
        raise ValueError("unexpected pending draw(s): "+repr(pending))
    return {"history":complete,"target":expected,
            "cutoff":complete[-1]["Issue"],
            "source_sha256":hashlib.sha256(raw).hexdigest(),
            "pending_source_record":bool(pending)}
