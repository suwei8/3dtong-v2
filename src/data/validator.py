"""Strict source validation: preserve three-character draw codes including 0-prefixes."""
import re

def validate_columns(columns):
    if not {"Issue", "KaiJiang"}.issubset(set(columns or ())):
        raise ValueError("CSV must contain Issue and KaiJiang")
    return True

def validate_rows(rows):
    if not rows:
        raise ValueError("empty history")
    seen=set()
    for row in rows:
        issue=str(row["Issue"]).strip()
        code=str(row["KaiJiang"]).strip()
        if not re.fullmatch(r"\d{7}",issue) or not re.fullmatch(r"\d{3}",code):
            raise ValueError("invalid issue or draw code")
        if issue in seen:
            raise ValueError("duplicate issue: "+issue)
        seen.add(issue)
    return True
