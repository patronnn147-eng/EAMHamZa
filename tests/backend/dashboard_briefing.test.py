from modules.shared.services.dashboard_briefing import (
    compute_facts, facts_hash, render_template, make_briefing, _CACHE,
)


def _facts(urgent=2, overdue=1, degraded=("P-07",)):
    return compute_facts(
        urgent_wos=urgent,
        pending_wos=3,
        completed_week=5,
        overdue_pms=overdue,
        degraded_machines=list(degraded),
        active_alerts=1,
    )


def test_compute_facts_shape():
    f = _facts()
    assert f["urgent_wos"] == 2
    assert f["overdue_pms"] == 1
    assert f["degraded_machines"] == ["P-07"]


def test_hash_stable_and_sensitive():
    assert facts_hash(_facts()) == facts_hash(_facts())
    assert facts_hash(_facts(urgent=2)) != facts_hash(_facts(urgent=9))


def test_template_is_nonempty_and_mentions_counts():
    text = render_template(_facts())
    assert isinstance(text, str) and text.strip()
    assert "2" in text  # urgent count surfaces


def test_make_briefing_uses_llm_then_caches():
    _CACHE.clear()
    calls = {"n": 0}

    def fake_llm(facts):
        calls["n"] += 1
        return "Generated briefing."

    r1 = make_briefing(_facts(), scope="role", scope_id="ADMIN", site="S1",
                       today="2026-06-18", llm_call=fake_llm)
    assert r1["text"] == "Generated briefing."
    assert r1["source"] == "llm"

    r2 = make_briefing(_facts(), scope="role", scope_id="ADMIN", site="S1",
                       today="2026-06-18", llm_call=fake_llm)
    assert r2["source"] == "cache"
    assert calls["n"] == 1  # second call served from cache


def test_make_briefing_falls_back_to_template_and_does_not_cache():
    _CACHE.clear()

    def boom_llm(facts):
        raise RuntimeError("llm down")

    r = make_briefing(_facts(), scope="role", scope_id="ADMIN", site="S1",
                      today="2026-06-18", llm_call=boom_llm)
    assert r["source"] == "template"
    assert r["text"].strip()
    # template result is NOT cached -> next call retries the LLM
    assert len(_CACHE) == 0
