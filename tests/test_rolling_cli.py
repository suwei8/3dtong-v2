"""End-to-end CLI verification on synthetic rows only."""
import csv
import json
import sys
from src.research import rolling


def test_cli_experiment_generates_chinese_aggregate_reports(tmp_path,monkeypatch):
    data=tmp_path/"fake.csv"
    with data.open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["Issue","KaiJiang"])
        writer.writeheader()
        for i in range(1,261):
            writer.writerow({"Issue":f"2023{i:03d}","KaiJiang":f"{(i*37+13)%1000:03d}"})
    output=tmp_path/"outputs"
    monkeypatch.setattr(sys,"argv",[
        "rolling","--data",str(data),"--out",str(output),
        "--holdout","20","--rounds","20","--refit-every","5","--min-train","90"
    ])
    rolling.main()
    summary=json.loads((output/"rolling-ablation.json").read_text(encoding="utf-8"))
    md=(output/"rolling-ablation.md").read_text(encoding="utf-8")
    assert summary["config"]["holdout_size"]==20
    assert all(v["samples"]==20 for v in summary["variants"].values())
    assert "滚动回测" in md
    assert "KaiJiang" not in md+json.dumps(summary)
