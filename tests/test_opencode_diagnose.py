"""Diagnose report shapes: raw provider evidence is extracted, never invented.

All CLI calls are mocked; these tests never invoke OpenCode or the network.
"""
import json
import subprocess
from types import SimpleNamespace
from src.pipeline import opencode_diagnose as diag


def error_event(error):
    return json.dumps({"type":"error","timestamp":1,"sessionID":"s","error":error})+"\n"


FREE_LIMIT={"type":"provider.free-limit","status":429,"retryAfterMs":26466000,
            "message":"Free usage limit reached.",
            "response":{"body":json.dumps({"error":{"type":"FreeUsageLimitError","message":"x"}})}}
NO_ROUTE={"type":"provider.no-route","message":"Model unavailable: opencode/gone"}


def test_extract_error_reads_last_error_event():
    stdout=(json.dumps({"type":"step_start","part":{}})+"\n"
            +error_event(FREE_LIMIT)
            +json.dumps({"type":"text","part":{"type":"text","text":"x"}})+"\n")
    assert diag.extract_error(stdout)==FREE_LIMIT
    assert diag.extract_error("")is None
    assert diag.extract_error("not json\n")is None


def test_nested_upstream_error_type_unwrapped():
    assert diag._nested_error_type(FREE_LIMIT)=="FreeUsageLimitError"
    assert diag._nested_error_type(NO_ROUTE)is None


def done(stdout="",stderr="",code=0):
    return SimpleNamespace(stdout=stdout,stderr=stderr,returncode=code)


def test_probe_records_raw_free_limit_evidence(monkeypatch,tmp_path):
    monkeypatch.setattr(subprocess,"run",
        lambda *a,**k: done(stdout=error_event(FREE_LIMIT),code=1))
    record=diag.probe("opencode","opencode/big-pickle",tmp_path,{},30)
    assert record["status"]=="error"
    assert record["error_type"]=="provider.free-limit"
    assert record["upstream_error_type"]=="FreeUsageLimitError"
    assert record["http_status"]==429
    assert record["retry_after_hours"]>7
    assert "raw_error" in record


def test_probe_records_no_route_and_reply(monkeypatch,tmp_path):
    monkeypatch.setattr(subprocess,"run",
        lambda *a,**k: done(stdout=error_event(NO_ROUTE),code=1))
    record=diag.probe("opencode","opencode/gone",tmp_path,{},30)
    assert record["status"]=="error" and record["error_type"]=="provider.no-route"
    ok_text=json.dumps({"type":"text","part":{"type":"text","text":'{"digits":[1,2,3]}'}})
    monkeypatch.setattr(subprocess,"run",lambda *a,**k: done(stdout=ok_text))
    record=diag.probe("opencode","opencode/good",tmp_path,{},30)
    assert record["status"]=="ok" and "digits" in record["reply_excerpt"]


def test_probe_timeout_and_spawn_error(monkeypatch,tmp_path):
    monkeypatch.setattr(subprocess,"run",
        lambda *a,**k:(_ for _ in ()).throw(subprocess.TimeoutExpired("opencode",30)))
    assert diag.probe("opencode","m",tmp_path,{},30)["status"]=="timeout"
    monkeypatch.setattr(subprocess,"run",
        lambda *a,**k:(_ for _ in ()).throw(OSError("missing")))
    assert diag.probe("opencode","m",tmp_path,{},30)["status"]=="spawn-error"


def test_catalogue_parses_only_model_lines(monkeypatch,tmp_path):
    stdout="opencode/a-free\nopencode/b\n banner junk \nhttps://x/y\n"
    monkeypatch.setattr(subprocess,"run",lambda *a,**k: done(stdout=stdout))
    record=diag.catalogue("opencode",tmp_path,{})
    assert record["listed"] and record["models"]==["opencode/a-free","opencode/b"]
    monkeypatch.setattr(subprocess,"run",lambda *a,**k: done(stderr="boom",code=1))
    assert diag.catalogue("opencode",tmp_path,{})["listed"] is False


def test_markdown_lists_missing_and_new_catalogue_models(tmp_path):
    info={"tested_at_utc":"t","cli":{"version":"opencode v2.1.4"},
          "summary":{"probed":2,"ok":0,"free_limit":1,"no_route":1},
          "catalogue":{"listed":True,
                       "configured_missing_from_listing":["opencode/old-free"],
                       "visible_not_configured":["opencode/new-free"]},
          "results":[{"model":"opencode/a","status":"error","error_type":"provider.free-limit",
                      "http_status":429,"retry_after_hours":7.1,
                      "in_catalogue_listing":True,"message":"m|pipe"}]}
    text=diag.markdown(info)
    assert "opencode/old-free" in text and "opencode/new-free" in text
    assert "\\|" in text and "provider.free-limit" in text
