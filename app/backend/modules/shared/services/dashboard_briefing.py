"""
Dashboard AI briefing — role-scoped facts, daily in-memory cache, LLM phrasing
with a rule-based template fallback. Pure orchestration lives here; the route
wires DB + Groq into it.

Mirrors the platform safety property: never raises. LLM down -> template.
Single-service deployment: an in-process dict cache is sufficient (no
cross-worker sharing needed).
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Callable, Dict, List

# In-memory cache: key -> {"text", "generated_at"}. Resets on restart (fine for
# a daily briefing). Stale-day entries are pruned on insert.
_CACHE: Dict[str, Dict[str, str]] = {}

# Only these fields influence the briefing text, so only they drive the cache
# hash — changes to other displayed metrics must not trigger spurious LLM calls.
_MATERIAL_KEYS = ("urgent_wos", "degraded_machines", "overdue_pms", "active_alerts")


def compute_facts(
    *,
    urgent_wos: int,
    pending_wos: int,
    completed_week: int,
    overdue_pms: int,
    degraded_machines: List[str],
    active_alerts: int,
) -> Dict:
    """Material facts that drive the briefing. Sync + pure -> unit-testable.

    degraded_machines is sorted so the hash is order-independent (DB queries
    without ORDER BY must not defeat the cache).
    """
    return {
        "urgent_wos": int(urgent_wos),
        "pending_wos": int(pending_wos),
        "completed_week": int(completed_week),
        "overdue_pms": int(overdue_pms),
        "degraded_machines": sorted(str(m) for m in degraded_machines),
        "active_alerts": int(active_alerts),
    }


def facts_hash(facts: Dict) -> str:
    """Stable hash over the briefing-material fields only (sorted keys)."""
    material = {k: facts.get(k) for k in _MATERIAL_KEYS}
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cache_key(scope: str, scope_id: str, site: str, today: str, h: str) -> str:
    """Collision-free key (JSON-encoded list -- no separator ambiguity)."""
    return json.dumps([scope, scope_id, site, today, h], ensure_ascii=False)


def render_template(facts: Dict) -> str:
    """Deterministic fallback text. No LLM. Always non-empty. Never raises."""
    parts = []
    if facts.get("urgent_wos"):
        parts.append(f"{facts['urgent_wos']} ordre(s) urgent(s) a traiter.")
    if facts.get("degraded_machines"):
        names = ", ".join(list(facts["degraded_machines"])[:3])
        parts.append(f"Machines a surveiller: {names}.")
    if facts.get("overdue_pms"):
        parts.append(f"{facts['overdue_pms']} maintenance(s) preventive(s) en retard.")
    if facts.get("active_alerts"):
        parts.append(f"{facts['active_alerts']} alerte(s) active(s).")
    if not parts:
        return "Tout est sous controle aujourd'hui. Aucune action urgente."
    return " ".join(parts)


def _prune_stale(today: str) -> None:
    """Drop cache entries from previous days to bound memory."""
    stale = []
    for k in _CACHE:
        try:
            if json.loads(k)[3] != today:
                stale.append(k)
        except Exception:
            stale.append(k)
    for k in stale:
        _CACHE.pop(k, None)


def make_briefing(
    facts: Dict,
    *,
    scope: str,
    scope_id: str,
    site: str,
    today: str,
    llm_call: Callable[[Dict], str],
) -> Dict:
    """
    Cache-first orchestration. Returns {"text", "generated_at", "source"}.
    source in {"cache","llm","template"}. Never raises.
    """
    key = cache_key(scope, scope_id, site, today, facts_hash(facts))

    hit = _CACHE.get(key)
    if hit:
        return {"text": hit["text"], "generated_at": hit["generated_at"], "source": "cache"}

    try:
        text = llm_call(facts)
        if not text or not text.strip():
            raise ValueError("empty LLM text")
        now = datetime.now(timezone.utc).isoformat()
        _prune_stale(today)
        _CACHE[key] = {"text": text, "generated_at": now}
        return {"text": text, "generated_at": now, "source": "llm"}
    except Exception:
        # Safety net must itself never raise. Do NOT cache the template --
        # next load retries the LLM.
        now = datetime.now(timezone.utc).isoformat()
        try:
            fallback = render_template(facts)
        except Exception:
            fallback = "Briefing indisponible pour le moment."
        return {"text": fallback, "generated_at": now, "source": "template"}
