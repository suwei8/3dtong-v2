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



def test_retired_space_bunny_is_replaced_only_in_new_contestants():
    approved,timeout=api.load_models()
    assert "opencode/minimax-m3.1-flash-free" in approved
    assert "opencode/space-bunny-free" not in approved
    assert len(approved)==9 and timeout==45


def test_retired_space_bunny_cannot_be_invoked_as_current_model():
    with pytest.raises(ValueError,match="approved"):
        api.predict_model('{"freq":3}',"opencode/space-bunny-free")



@pytest.mark.parametrize(("message","reason"),[
    ("OpenCode's free tier can only be used from within OpenCode",
     "free-tier gateway tool/permission"),
    ("FreeUsageLimitError status=429","rate limit (429)"),
    ("ProviderModelNotFoundError","model ID missing"),
    ("Model has been deprecated","retired or deprecated"),
    ("Error HTTP 403 Forbidden","gateway forbidden"),
    ("Unknown provider diagnostic","unclassified"),
])
def test_model_error_categorizer_never_prints_raw_provider_message(message,reason):
    answer=api.classify_cli_failure("",message+" SECURITY_SENSITIVE_STRING")
    assert reason in answer
    assert "SECURITY_SENSITIVE_STRING" not in answer


def test_nonzero_cli_result_classifies_safe_gateway_error(monkeypatch):
    monkeypatch.setattr(api.shutil,"which",lambda _: "/usr/bin/opencode")
    def fake_run(*args,**kwargs):
        return SimpleNamespace(returncode=1,stdout="",
                               stderr="OpenCode's free tier can only be used from within OpenCode")
    monkeypatch.setattr(api.subprocess,"run",fake_run)
    result=api.predict_model('{"freq":3}',"opencode/minimax-m3.1-flash-free")
    assert result["status"]=="skipped"
    assert "free-tier gateway" in result["reason"]


def test_zero_exit_with_error_event_is_categorized(monkeypatch):
    monkeypatch.setattr(api.shutil,"which",lambda _: "/usr/bin/opencode")
    stdout=json.dumps({"type":"error","error":{"name":"FreeUsageLimitError",
                                                "message":"429 Too Many Requests"}})+"\n"
    monkeypatch.setattr(api.subprocess,"run",lambda *args,**kwargs:
                        SimpleNamespace(returncode=0,stdout=stdout,stderr=""))
    result=api.predict_model('{"freq":3}',"opencode/minimax-m3.1-flash-free")
    assert result["status"]=="skipped"
    assert "429" in result["reason"]
