"""Load only historical fields required for prediction; never expose source data in public outputs."""
import csv
from pathlib import Path
from .validator import validate_columns, validate_rows

def load_history(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader=csv.DictReader(stream)
        validate_columns(reader.fieldnames)
        rows=[{"Issue": r["Issue"].strip(), "KaiJiang": r["KaiJiang"].strip()} for r in reader]
    validate_rows(rows)
    return sorted(rows,key=lambda r:int(r["Issue"]))
