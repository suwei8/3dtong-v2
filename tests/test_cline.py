"""CLI schema, safe environment and failure contract; no paid API request."""
import json
from types import SimpleNamespace
import pytest
from src.models.llm.cline_mimo import ClineMimoPredictor,parse_run_result
from src.models.llm.contestant import summary_for_llm

def event(text):
    return json.dumps({"type":"agent_event","text":"irrelevant"})+"\n"+json.dumps({"type":"run_result","text":text})+"\n"

def test_final_event():
    assert parse_run_result(event('{"digits":[1,4,9]}'))==[1,4,9]

@pytest.mark.parametrize("text",[
    "done", '{"digits":[1,1,3]}', '{"digits":[1,true,9]}',
    '{"digits":["1",4,9]}', '{"digits":[10,2,3]}',
    '{"digits":[0,1,2],"other":7}'
])
def test_invalid_answer(text):
    with pytest.raises(ValueError):
        parse_run_result(event(text))

def test_no_final_event():
    with pytest.raises(ValueError):
        parse_run_result('{"type":"agent_event","text":"ok"}')

def test_summary_does_not_copy_private_rows():
    history=[{"Issue":f"2025{i:03d}","KaiJiang":"908"} for i in range(1,131)]
    s=summary_for_llm(history)
    obj=json.loads(s)
    assert obj["as_of_issue"]=="2025130"
    assert "KaiJiang" not in s

def test_cli_scrubs_sensitive_tokens(monkeypatch,tmp_path):
    from src.models.llm import cline_mimo
    captured={}
    monkeypatch.setenv("GITHUB_TOKEN","never-send")
    monkeypatch.setenv("PINBLE_DATA_TOKEN","never-send")
    monkeypatch.setenv("CLINE_API_KEY","test-key")
    monkeypatch.setattr(cline_mimo.shutil,"which",lambda _:"/usr/bin/cline")
    def fake(cmd,**kwargs):
        captured.update(kwargs)
        assert "--auto-approve" in cmd and cmd[cmd.index("--auto-approve")+1]=="false"
        return SimpleNamespace(returncode=0,stdout=event('{"digits":[0,6,8]}'))
    monkeypatch.setattr(cline_mimo.subprocess,"run",fake)
    result=ClineMimoPredictor().predict("counts",cwd=tmp_path)
    assert result["status"]=="ok" and result["digits"]==[0,6,8]
    assert "GITHUB_TOKEN" not in captured["env"]
    assert "PINBLE_DATA_TOKEN" not in captured["env"]
    assert captured["env"]["CLINE_API_KEY"]=="test-key"

def test_no_cli_is_skipped(monkeypatch,tmp_path):
    from src.models.llm import cline_mimo
    monkeypatch.setattr(cline_mimo.shutil,"which",lambda _ : None)
    assert ClineMimoPredictor().predict("counts",cwd=tmp_path)["status"]=="skipped"

def test_workspace_must_be_empty(tmp_path):
    (tmp_path/"private.csv").write_text("do not expose")
    with pytest.raises(ValueError):
        ClineMimoPredictor().predict("counts",cwd=tmp_path)
