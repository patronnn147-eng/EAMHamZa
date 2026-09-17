"""
EAM Multi-Agent Orchestrator.

Three sequential specialized agents, all using Groq (no extra deps):

  Agent 1 — DataCollector  : decides which tools to call, fetches EAM data
  Agent 2 — Analyst        : diagnoses problems from collected data
  Agent 3 — Planner        : produces prioritized action recommendations

Each agent is a focused Groq call with a narrow system prompt.
Results flow: collector → analyst → planner → final structured response.
"""

import json
import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from core.groq_client import get_groq_client
from services.ai_tools import get_tool_definitions, execute_tool

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Agent system prompts
# ---------------------------------------------------------------------------

COLLECTOR_SYSTEM = """Tu es un agent de collecte de donnees pour un systeme EAM industriel.
Ton role: analyser la requete utilisateur et appeler les outils necessaires pour collecter les donnees pertinentes.
Tu dois appeler TOUS les outils utiles pour repondre completement a la requete.
Appelle plusieurs outils si necessaire. Sois exhaustif."""

ANALYST_SYSTEM = """Tu es un analyste de maintenance industrielle expert.
Tu recois des donnees EAM brutes et tu produis une analyse technique concise:
- Etat actuel des actifs concernes
- Problemes identifies (pannes, risques, retards)
- Tendances et patterns remarquables
- Niveau de criticite global (CRITIQUE / ELEVE / MOYEN / FAIBLE)

Sois factuel et precis. Base-toi uniquement sur les donnees fournies."""

PLANNER_SYSTEM = """Tu es un planificateur de maintenance industrielle expert.
Tu recois une analyse de situation et tu produis un plan d'action structure:

FORMAT DE REPONSE OBLIGATOIRE (JSON):
{
  "criticite": "CRITIQUE|ELEVE|MOYEN|FAIBLE",
  "resume": "resume en 1-2 phrases",
  "actions": [
    {
      "priorite": 1,
      "action": "description action",
      "responsable": "TECHNICIEN|CHEFTECH|ADMIN",
      "delai": "immediat|24h|48h|1 semaine",
      "machine_id": null
    }
  ],
  "risques": ["risque 1", "risque 2"],
  "kpis_a_surveiller": ["KPI 1", "KPI 2"]
}

Reponds UNIQUEMENT avec le JSON valide, sans markdown ni explication."""


# ---------------------------------------------------------------------------
# Agent 1 — Data Collector
# ---------------------------------------------------------------------------


async def run_collector(
    query: str,
    db: AsyncSession,
    role: str = "TECHNICIEN",
) -> Dict[str, Any]:
    """
    Calls EAM tools based on the user query.
    Returns collected data dict keyed by tool name.
    """
    groq = get_groq_client()
    tools = get_tool_definitions()

    messages = [
        {"role": "system", "content": COLLECTOR_SYSTEM},
        {"role": "user", "content": f"Requete: {query}\nRole utilisateur: {role}"},
    ]

    try:
        response = groq.chat(messages=messages, tools=tools, temperature=0.1)
    except Exception as e:
        logger.exception(f"Collector agent Groq error: {e}")
        raise

    choices = response.get("choices", [])
    if not choices:
        return {}

    msg = choices[0].get("message", {})
    tool_calls = msg.get("tool_calls", [])

    if not tool_calls:
        # No tools called — return empty, analyst will work with nothing
        logger.warning("Collector: no tools called for query")
        return {}

    collected: Dict[str, Any] = {}
    for tc in tool_calls:
        func_name = tc["function"]["name"]
        func_args_raw = tc["function"]["arguments"]
        func_args = (
            json.loads(func_args_raw)
            if isinstance(func_args_raw, str)
            else func_args_raw
        )
        try:
            result = await execute_tool(func_name, func_args, db)
            collected[func_name] = result
            logger.info(
                f"Collector: {func_name} returned {len(result) if isinstance(result, list) else 1} items"
            )
        except Exception as e:
            logger.exception(f"Collector: tool {func_name} failed: {e}")
            collected[func_name] = {"error": str(e)}

    return collected


# ---------------------------------------------------------------------------
# Agent 2 — Analyst
# ---------------------------------------------------------------------------


def run_analyst(query: str, collected_data: Dict[str, Any]) -> str:
    """
    Produces technical diagnostic from collected EAM data.
    Returns analysis string.
    """
    groq = get_groq_client()

    if not collected_data:
        data_summary = "Aucune donnee collectee. Informe que la requete ne correspond a aucune donnee disponible."
    else:
        # Truncate large datasets before sending to analyst
        truncated = {}
        for tool_name, data in collected_data.items():
            if isinstance(data, list):
                truncated[tool_name] = data[:15]  # top 15 per tool
            else:
                truncated[tool_name] = data
        data_summary = json.dumps(truncated, ensure_ascii=False, default=str, indent=2)

    messages = [
        {"role": "system", "content": ANALYST_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Requete originale: {query}\n\nDonnees collectees:\n{data_summary}"
            ),
        },
    ]

    try:
        response = groq.chat(messages=messages, temperature=0.2)
        choices = response.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "") or ""
    except Exception as e:
        logger.exception(f"Analyst agent Groq error: {e}")
        raise

    return ""


# ---------------------------------------------------------------------------
# Agent 3 — Planner
# ---------------------------------------------------------------------------


def run_planner(query: str, analysis: str) -> Dict[str, Any]:
    """
    Produces structured action plan from analyst output.
    Returns parsed JSON plan dict.
    """
    groq = get_groq_client()

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Requete originale: {query}\n\nAnalyse de situation:\n{analysis}"
            ),
        },
    ]

    try:
        response = groq.chat(messages=messages, temperature=0.1)
        choices = response.get("choices", [])
        if not choices:
            return _fallback_plan("Aucune reponse du planificateur.")

        content = choices[0].get("message", {}).get("content", "") or ""

        # Strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(
                ln for ln in lines if not ln.strip().startswith("```")
            ).strip()

        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.warning(f"Planner JSON parse failed: {e}. Raw: {content[:200]}")
        return _fallback_plan(content)
    except Exception as e:
        logger.exception(f"Planner agent Groq error: {e}")
        raise


def _fallback_plan(note: str) -> Dict[str, Any]:
    return {
        "criticite": "INCONNU",
        "resume": note,
        "actions": [],
        "risques": [],
        "kpis_a_surveiller": [],
    }


# ---------------------------------------------------------------------------
# Orchestrator — runs all three agents sequentially
# ---------------------------------------------------------------------------


async def run_eam_analysis(
    query: str,
    db: AsyncSession,
    role: str = "TECHNICIEN",
) -> Dict[str, Any]:
    """
    Full multi-agent EAM analysis pipeline.

    Args:
        query: Natural language question/request
        db: Async DB session for tool execution
        role: User role for scoping

    Returns:
        {
            "analysis": str,          # Analyst narrative
            "plan": dict,             # Structured action plan from Planner
            "data_sources": list,     # Tools called + item counts
            "query": str,
        }
    """
    logger.info(f"EAM analysis pipeline starting for query: {query[:80]}")

    # Agent 1 — collect data
    collected = await run_collector(query, db, role)
    data_sources = [
        {
            "tool": tool,
            "count": len(v) if isinstance(v, list) else (0 if "error" in v else 1),
        }
        for tool, v in collected.items()
    ]

    # Agent 2 — analyse
    analysis = run_analyst(query, collected)

    # Agent 3 — plan
    plan = run_planner(query, analysis)

    logger.info(
        f"EAM analysis complete | tools={[s['tool'] for s in data_sources]} "
        f"| criticite={plan.get('criticite')}"
    )

    return {
        "query": query,
        "analysis": analysis,
        "plan": plan,
        "data_sources": data_sources,
    }
