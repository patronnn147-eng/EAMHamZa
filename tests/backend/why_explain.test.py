import modules.shared.routes.why as why


def test_make_explanation_uses_llm_then_caches():
    why._CACHE.clear()
    calls = {"n": 0}

    def fake_llm(reasons):
        calls["n"] += 1
        return "Explication simple."

    r1 = why.make_explanation(["trop chaud", "usure élevée"], llm_call=fake_llm)
    assert r1["source"] == "llm" and r1["text"] == "Explication simple."
    r2 = why.make_explanation(["trop chaud", "usure élevée"], llm_call=fake_llm)
    assert r2["source"] == "cache"
    assert calls["n"] == 1


def test_make_explanation_falls_back_to_joined_reasons():
    why._CACHE.clear()

    def boom(reasons):
        raise RuntimeError("down")

    r = why.make_explanation(["trop chaud", "usure élevée"], llm_call=boom)
    assert r["source"] == "fallback"
    assert "trop chaud" in r["text"] and "usure élevée" in r["text"]


def test_empty_reasons_returns_safe_text():
    why._CACHE.clear()
    r = why.make_explanation([], llm_call=lambda x: "")
    assert r["text"].strip()
