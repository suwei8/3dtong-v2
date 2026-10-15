import json
from src.pipeline import probe_free_models as probe


def test_synthetic_chain_produces_vote_and_hybrid(tmp_path,monkeypatch):
    models=["opencode/a","opencode/b","opencode/c"]
    monkeypatch.setattr(probe,"load_models",lambda : (models,35))
    seq={"opencode/a":[1,3,6],"opencode/b":[1,3,8],"opencode/c":[1,3,9]}
    monkeypatch.setattr(probe,"predict_model",lambda _,name,timeout: {
        "model":name,"status":"ok","digits":seq[name]})
    output=probe.run(out=tmp_path)
    assert output["kind"]=="anonymous-cli-availability-only"
    assert output["synthetic_data_only"]
    assert output["derived_synthetic"]["opencode-consensus"]["status"]=="ok"
    assert output["derived_synthetic"]["ml-opencode-hybrid"]["status"]=="ok"
    assert (tmp_path/"opencode-availability.md").is_file()
    assert "合成数据" in (tmp_path/"opencode-availability.md").read_text(encoding="utf-8")
    assert not any("KaiJiang" in k for k in output)


def test_three_unavailable_models_do_not_create_synthetic_votes(tmp_path,monkeypatch):
    monkeypatch.setattr(probe,"load_models",lambda : (
        ["opencode/a","opencode/b","opencode/c"],35))
    monkeypatch.setattr(probe,"predict_model",lambda _,name,timeout: {
        "model":name,"status":"skipped","reason":"offline"})
    info=probe.run(out=tmp_path)
    assert info["derived_synthetic"]["opencode-consensus"]["status"]=="skipped"
    assert "synthetic_response_digits" not in info["derived_synthetic"]["ml-opencode-hybrid"]
