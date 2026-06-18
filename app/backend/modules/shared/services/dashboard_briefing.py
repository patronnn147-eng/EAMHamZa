"""
Dashboard AI briefing — role-scoped facts, daily in-memory cache, LLM phrasing
with a rule-based template fallback. Pure orchestration lives here; the route
wires DB + Groq into it.

Mirrors the platform safety property: never raises. LLM down -> template.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Callable, Dict, List

# In-memory cache: key -> {"text", "generated_at"}. Resets on restart (fine for
# a daily briefing). Matches the in-memory cache convention used elsewhere.
_CACHE: Dict[str, Dict[str, str]] = {}


def compute_facts(
    *,
    urgent_wos: int,
    pending_wos: int,
    completed_week: int,
    overdue_pms: int,
    degraded_machines: List[str],
    active_alerts: int,
) -> Dict:
    """Material facts that drive the briefing. Sync + pure -> unit-testable."""
    return {
        "urgent_wos": int(urgent_wos),
        "pending_wos": int(pending_wos),
        "completed_week": int(completed_week),
        "overdue_pms": int(overdue_pms),
        "degraded_machines": list(degraded_machines),
        "active_alerts": int(active_alerts),
    }


def facts_hash(facts: Dict) -> str:
    """Stable hash over material facts only (sorted keys)."""
    blob = json.dumps(facts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def cache_key(scope: str, scope_id: str, site: str, today: str, h: str) -> str:
    return f"{scope}|{scope_id}|{site}|{today}|{h}"


def render_template(facts: Dict) -> str:
    """Deterministic fallback text. No LLM. Always non-empty."""
    parts = []
    if facts["urgent_wos"]:
        parts.append(f"{facts['urgent_wos']} ordre(s) urgent(s) a traiter.")
    if facts["degraded_machines"]:
        names = ", ".join(facts["degraded_machines"][:3])
        parts.append(f"Machines a surveiller: {names}.")
    if facts["overdue_pms"]:
        parts.append(f"{facts['overdue_pms']} maintenance(s) preventive(s) en retard.")
    if facts["active_alerts"]:
        parts.append(f"{facts['active_alerts']} alerte(s) active(s).")
    if not parts:
        return "Tout est sous controle aujourd'hui. Aucune action urgente."
    return " ".join(parts)


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

    now = datetime.now(timezone.utc).isoformat()
    try:
        text = llm_call(facts)
        if not text or not text.strip():
            raise ValueError("empty LLM text")
        _CACHE[key] = {"text": text, "generated_at": now}
        return {"text": text, "generated_at": now, "source": "llm"}
    except Exception:
        # Do NOT cache the template -- next load retries the LLM.
        return {"text": render_template(facts), "generated_at": now, "source": "template"}
