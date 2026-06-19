"""Dashboard command-center endpoints. Auto-discovered via main.py router scan."""
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from core.groq_client import get_groq_client
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from models.ordres_travail import Ordres_travail, OrdreStatut

from modules.shared.services.dashboard_briefing import compute_facts, make_briefing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# Work-order statuses that count as "finished" (not open work).
_TERMINAL = [
    OrdreStatut.COMPLETED,
    OrdreStatut.VALIDATED,
    OrdreStatut.CLOSED,
    OrdreStatut.REJECTED,
    OrdreStatut.ANNULÉ,
]
_PENDING = [OrdreStatut.SUBMITTED, OrdreStatut.APPROVED, OrdreStatut.ASSIGNED]
_COMPLETED = [OrdreStatut.COMPLETED, OrdreStatut.VALIDATED, OrdreStatut.CLOSED]
# Machine statuses that mean "needs attention".
_DOWN = ["EN_PANNE", "HORS_SERVICE"]


class BriefingResponse(BaseModel):
    text: str
    generated_at: str
    source: str
    facts: dict = {}


def _llm_call(facts: dict) -> str:
    """Phrase the facts in one short French paragraph. Raises on any failure."""
    prompt = (
        "Tu es l'assistant maintenance. Redige UN court paragraphe (2-3 phrases, "
        "ton professionnel, en francais) resumant l'etat du jour a partir de ces faits. "
        "Pas de liste, pas de markdown.\n"
        f"Faits: {facts}"
    )
    groq = get_groq_client()
    resp = groq.chat(messages=[{"role": "user", "content": prompt}])
    return resp["choices"][0]["message"]["content"]


async def _gather_facts(role: str, user_id, db: AsyncSession) -> dict:
    """Build the role-scoped material facts. Best-effort; missing data -> zeros."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    async def _count(stmt) -> int:
        try:
            res = await db.execute(stmt)
            return int(res.scalar_one() or 0)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"[dashboard] count failed: {e}")
            return 0

    base_wo = select(func.count()).select_from(Ordres_travail)
    if role == "TECHNICIEN" and user_id is not None:
        base_wo = base_wo.where(Ordres_travail.utilisateur_id == user_id)

    urgent = await _count(base_wo.where(
        Ordres_travail.priorite == "URGENTE",
        Ordres_travail.statut.notin_(_TERMINAL)))
    pending = await _count(base_wo.where(Ordres_travail.statut.in_(_PENDING)))
    completed = await _count(base_wo.where(
        Ordres_travail.statut.in_(_COMPLETED),
        Ordres_travail.created_at >= week_ago))

    overdue = await _count(select(func.count()).select_from(Machines).where(
        Machines.date_prochaine_maintenance < now))

    degraded: List[str] = []
    try:
        res = await db.execute(
            select(Machines.nom).where(Machines.statut.in_(_DOWN)).limit(3))
        degraded = [r[0] for r in res.all()]
    except Exception:
        degraded = []

    return compute_facts(
        urgent_wos=urgent, pending_wos=pending, completed_week=completed,
        overdue_pms=overdue, degraded_machines=degraded, active_alerts=0,
    )


@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing(
    site: str = Query(default="all"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    Daily AI briefing. Role-scoped facts, cache-first, LLM on miss,
    template fallback when the LLM is unavailable. Never raises.
    """
    role = current_user.role.value if current_user.role else "TECHNICIEN"
    today = datetime.now(timezone.utc).date().isoformat()

    if role == "TECHNICIEN":
        scope, scope_id = "user", str(current_user.id)
    else:
        scope, scope_id = "role", role

    facts = await _gather_facts(role, current_user.id, db)
    result = make_briefing(
        facts, scope=scope, scope_id=scope_id, site=site,
        today=today, llm_call=_llm_call,
    )
    return BriefingResponse(**result, facts=facts)
