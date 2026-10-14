from pathlib import Path
import csv

REQUIRED_FIELDS = ["KaiJiang"]


def load_history(path: str):
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for field in REQUIRED_FIELDS:
        if rows and field not in rows[0]:
            raise ValueError(f"missing field: {field}")
    return rows
