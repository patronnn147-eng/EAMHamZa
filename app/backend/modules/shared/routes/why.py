"""Plain-language 'Why?' explanation endpoint. Cached LLM, never raises."""

import hashlib
import json
import logging
from typing import Callable, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from core.groq_client import get_groq_client
from models.utilisateurs import Utilisateurs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/why", tags=["why"])

_CACHE: dict = {}


def _key(reasons: List[str]) -> str:
    blob = json.dumps(reasons, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _llm(reasons: List[str]) -> str:
    prompt = (
        "Reformule ces points en UN paragraphe court, en français simple, "
        "pour un opérateur non technique. Aucun terme technique, pas de chiffres "
        "de modèle, pas de liste.\nPoints: " + " ; ".join(reasons)
    )
    resp = get_groq_client().chat(messages=[{"role": "user", "content": prompt}])
    return resp["choices"][0]["message"]["content"]


def make_explanation(
    reasons: List[str], *, llm_call: Callable[[List[str]], str]
) -> dict:
    """Cache-first plain-language phrasing. Never raises."""
    safe = [r for r in (reasons or []) if r and r.strip()]
    if not safe:
        return {"text": "Aucune raison particulière à signaler.", "source": "fallback"}
    key = _key(safe)
    if key in _CACHE:
        return {"text": _CACHE[key], "source": "cache"}
    try:
        text = llm_call(safe)
        if not text or not text.strip():
            raise ValueError("empty")
        _CACHE[key] = text
        return {"text": text, "source": "llm"}
    except Exception:
        return {"text": ". ".join(safe) + ".", "source": "fallback"}


class WhyExplainRequest(BaseModel):
    reasons: List[str]


class WhyExplainResponse(BaseModel):
    text: str
    source: str


@router.post("/explain", response_model=WhyExplainResponse)
async def explain(
    body: WhyExplainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    return WhyExplainResponse(**make_explanation(body.reasons, llm_call=_llm))
