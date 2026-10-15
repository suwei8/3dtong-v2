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


def sample_history():
    return [
        {"Issue":f"{year}{seq:03d}","KaiJiang":f"{(year+seq)%1000:03d}"}
        for year in (2023,2024,2025,2026)
        for seq in range(1,367 if year==2024 else 366)
    ]


def test_next_issue_rollover():
    assert next_issue("2026365")=="2027001"
    assert next_issue("2024366")=="2025001"
    assert next_issue("2026273")=="2026274"
    with pytest.raises(ValueError):
        next_issue("2026366")


def test_pending_next_issue_is_not_a_training_target(tmp_path):
    p=tmp_path/"data.csv"
    rows=sample_history()
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
    write_data(p,sample_history())
    import src.pipeline.live as live
    monkeypatch.setattr(live,"train_all",lambda rows:{"scores":{"fake":{"validation_hit_rate":.5}},
         "champion_validation_only":"fake","predictions":{"fake":[0,1,2]}})
    dest=tmp_path/"prediction"
    assert freeze_live(p,dest)
    frozen=dest/"runs"/"2027001.json"
    before=frozen.read_bytes()
    assert not freeze_live(p,dest)
    assert frozen.read_bytes()==before


def test_live_public_report_hides_actual(tmp_path):
    from src.pipeline.evaluate_live import evaluate_live
    data={"type":"prospective-next-issue","target_issue":"2026274",
          "known_through_issue":"2026273","generated_at_utc":"2026-10-15T03:00:00+00:00",
          "models":{"model":[0,1,2]}}
    result=evaluate_live(data,{"2026274":"902"})
    assert result["scores"]["model"] is True
    assert "902" not in json.dumps(result)
    assert evaluate_live(data,{}) is None
