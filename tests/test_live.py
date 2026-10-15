import csv
import json
import pytest
from src.data.live import next_issue,load_live_history
from src.pipeline.live import freeze_live


def write_data(path,rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["Issue","KaiJiang"])
        w.writeheader()
        w.writerows(rows)


def test_next_issue_rollover():
    assert next_issue("2026365")=="2027001"
    assert next_issue("2024366")=="2025001"
    assert next_issue("2026273")=="2026274"
    with pytest.raises(ValueError):
        next_issue("2026366")


def test_pending_next_issue_is_not_a_training_target(tmp_path):
    p=tmp_path/"data.csv"
    rows=[{"Issue":f"2026{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,366)]
    # Additional 1,000 prior draws make it large enough for true validation.
    rows=[{"Issue":f"2023{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,366)]+[
        {"Issue":f"2024{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,367)]+[
        {"Issue":f"2025{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,366)]+rows
    rows.append({"Issue":"2027001","KaiJiang":""})
    write_data(p,rows)
    source=load_live_history(p)
    assert source["target"]=="2027001"
    assert source["cutoff"]=="2026365"
    assert source["pending_source_record"]
    assert len(source["history"])==1461


def test_refuse_gap_or_too_short(tmp_path):
    p=tmp_path/"data.csv"
    write_data(p,[{"Issue":"2026273","KaiJiang":"902"},
                  {"Issue":"2026275","KaiJiang":""}])
    with pytest.raises(ValueError):
        load_live_history(p)


def test_live_never_overwrites_frozen(tmp_path,monkeypatch):
    p=tmp_path/"data.csv"
    write_data(p,[{"Issue":f"2025{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,366)]+[
        {"Issue":f"2026{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,366)]+[
        {"Issue":f"2024{i:03d}","KaiJiang":f"{i%1000:03d}"} for i in range(1,367)])
    # Source itself must contain enough known draws.
    import src.pipeline.live as live
    class Dummy:
        pass
    monkeypatch.setattr(live,"train_all",lambda rows:{"scores":{"fake":{"validation_hit_rate":.5}},
         "champion_validation_only":"fake","predictions":{"fake":[0,1,2]}})
    dest=tmp_path/"prediction"
    assert freeze_live(p,dest)
    frozen=dest/"runs"/"2027001.json"
    before=frozen.read_bytes()
    assert not freeze_live(p,dest)
    assert frozen.read_bytes()==before
