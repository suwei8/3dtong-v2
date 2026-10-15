import json
from types import SimpleNamespace
import pytest
from src.models.llm import opencode_free as api


def event(text):
    return json.dumps({"type":"step_start","part":{"type":"step-start"}})+"\n"+json.dumps(
        {"type":"text","part":{"type":"text","text":text}})+"\n"

def test_accepts_only_real_text_event_json():
    assert api.parse_json_events(event('{"digits":[0,5,8]}'))==[0,5,8]
    assert api.parse_json_events(event('{"digits":[0,')+event('5,8]}'))==[0,5,8]

@pytest.mark.parametrize("bad",[
    "hello","[]", '{"digits":[0,0,1]}', '{"digits":[0,1,true]}',
    '{"digits":[0,1,11]}', '{"digits":["0",1,2]}', '{"digits":[0,1,2],"secret":"x"}'
])
def test_reject_invalid_outputs(bad):
    with pytest.raises(ValueError):
        api.parse_json_events(event(bad))

def test_event_error_fails_closed():
    with pytest.raises(ValueError):
        api.parse_json_events('{"type":"error","error":"failure"}\n'+event('{"digits":[1,2,3]}'))

def test_clean_workspace_and_secret_scrub(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN","secret-1")
    monkeypatch.setenv("PINBLE_DATA_TOKEN","secret-2")
    monkeypatch.setenv("OPENAI_API_KEY","secret-3")
    monkeypatch.setattr(api.shutil,"which",lambda _: "/usr/bin/opencode")
    def fake_run(cmd,**kwargs):
        assert cmd[:5]==["opencode","run","--format","json","--model"]
        assert "GITHUB_TOKEN" not in kwargs["env"]
        assert "PINBLE_DATA_TOKEN" not in kwargs["env"]
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert kwargs["cwd"].joinpath("opencode.json").is_file()
        config=json.loads(kwargs["cwd"].joinpath("opencode.json").read_text())
        assert config["permission"]["*"]=="ask"
        assert config["permission"]["edit"]=="deny"
        assert config["permission"]["webfetch"]=="deny"
        return SimpleNamespace(returncode=0,stdout=event('{"digits":[3,4,9]}'))
    monkeypatch.setattr(api.subprocess,"run",fake_run)
    r=api.predict_model('{"freq":3}',"opencode/mimo-v2.6-flash-free")
    assert r["status"]=="ok" and r["digits"]==[3,4,9]

def test_missing_cli_skipped(monkeypatch):
    monkeypatch.setattr(api.shutil,"which",lambda _: None)
    result=api.predict_model('{"freq":3}',"opencode/mimo-v2.6-flash-free")
    assert result["status"]=="skipped" and "digits" not in result

def test_known_nine_models():
    ids,timeout=api.load_models()
    assert len(ids)==9 and len(set(ids))==9 and timeout>=5
    assert all(m.startswith("opencode/") for m in ids)
