"""System prompt templates and context builders for AI chat."""
import json
from typing import Dict, List, Any, Optional, Union

# Tool result types — what execute_tool() in ai_tools.py can return:
#   - list[dict] : row results (search_machines, get_work_orders, etc.)
#   - dict       : either an error envelope {"error": "..."} or a single record
#   - str        : pre-formatted string (rare; legacy)
ToolResult = Union[List[Dict[str, Any]], Dict[str, Any], str]


def get_system_prompt(role: str, user_name: str = "User") -> str:
    """
    Generate base system prompt by user role.

    Args:
        role: User role (ADMIN, CHEFTECH, CHETOP, TECHNICIEN)
        user_name: User's name for personalization

    Returns:
        System prompt string
    """
    base_prompt = (
        f"Tu es un assistant IA pour le systeme de gestion d'actifs industriels (EAMS).\n"
        f"Tu reponds en francais de maniere claire et concise.\n"
        f"Ta mission est d'aider les utilisateurs a trouver des informations et effectuer des taches.\n"
        f"Utilisateur actuel: {user_name}"
    )

    role_prompts: Dict[str, str] = {
        "ADMIN": (
            f"{base_prompt}\n\n"
            "Tu as acces complet au systeme:\n"
            "- Toutes les machines, tous les ordres de travail, toutes les interventions\n"
            "- Plannings, alertes, analytiques\n"
            "- Tu peux creer, modifier, supprimer\n\n"
            "Utilise des formats structures pour les donnees (tableaux, listes).\n"
            "Donne des informations completes incluant couts et statistiques."
        ),
        "CHEFTECH": (
            f"{base_prompt}\n\n"
            "Tu as acces technique:\n"
            "- Machines, interventions, plannings, alertes\n"
            "- Ordres de travail pour ton equipe\n"
            "- Analyse technique et maintenance\n\n"
            "Sois precis sur les specifications techniques et etat des machines."
        ),
        "CHETOP": (
            f"{base_prompt}\n\n"
            "Tu as acces production:\n"
            "- Ordres de travail, demandes d'intervention\n"
            "- Planning de la production\n"
            "- Suivi des operations\n\n"
            "Aide a coordonner la production et les ressources."
        ),
        "TECHNICIEN": (
            f"{base_prompt}\n\n"
            "Tu as acces terrain:\n"
            "- Tes ordres de travail assignes\n"
            "- Machines qui te sont attribuees\n"
            "- Interventions a realiser\n\n"
            "Aide a prioriser les taches et trouver les informations dont tu as besoin."
        ),
    }

    return role_prompts.get(role, base_prompt)


def build_memory_context(memories: List[Any]) -> str:
    """
    Format user memories into a system prompt section.

    Args:
        memories: List of AIMemories ORM objects

    Returns:
        Memory context string, empty string if no memories
    """
    if not memories:
        return ""

    preferences = []
    strategies = []
    failures = []

    for mem in memories:
        entry = f"  - {mem.memory_key}: {mem.memory_value}"
        if mem.memory_type == "preference":
            preferences.append(entry)
        elif mem.memory_type == "strategy":
            strategies.append(entry)
        elif mem.memory_type == "failure":
            failures.append(entry)

    sections = []
    if preferences:
        sections.append("Preferences utilisateur:\n" + "\n".join(preferences))
    if strategies:
        sections.append("Strategies efficaces:\n" + "\n".join(strategies))
    if failures:
        sections.append("Erreurs passees a eviter:\n" + "\n".join(failures))

    if not sections:
        return ""

    return "\n\n[MEMOIRE UTILISATEUR]\n" + "\n\n".join(sections) + "\n[FIN MEMOIRE]"


def build_rag_context(chunks: List[Any]) -> str:
    """
    Format RAG chunks into a [CONTEXTE DOCUMENTAIRE] section for the system prompt.

    Args:
        chunks: List of {content, metadata, similarity} dicts from RAG retriever

    Returns:
        Formatted context string, empty string if no chunks
    """
    if not chunks:
        return ""

    lines = [
        "\n\n[CONTEXTE DOCUMENTAIRE]",
        "INSTRUCTION CRITIQUE: Les extraits ci-dessous proviennent de la base documentaire officielle.",
        "Tu DOIS repondre en priorite depuis ce contexte documentaire.",
        "N'utilise PAS les outils de recherche si la reponse est dans ces extraits.",
        "Cite la source (nom du fichier) dans ta reponse.",
    ]
    for chunk in chunks:
        meta = chunk.get("metadata", {}) or {}
        source = meta.get("filename", "Document")
        page = meta.get("page")
        page_str = f" (page {page})" if page else ""
        sim = chunk.get("similarity", 0)
        lines.append(f"\nSource: {source}{page_str} (similarite: {sim:.0%})")
        lines.append(f"Contenu: {chunk['content'][:1500]}")
    lines.append("\n[FIN CONTEXTE DOCUMENTAIRE]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ML context — live prediction injection for machine-scoped chat
# ---------------------------------------------------------------------------

# Sensor thresholds per machine category — source: SAG-MNT-001 Section 6.
# Tuple: (warn_lo, warn_hi, crit_lo, crit_hi). None = no lower bound.
# Inside warn band = NORMAL; outside warn but inside crit = ATTENTION; outside crit = CRITIQUE.
_SENSOR_THRESHOLDS: Dict[str, Dict[str, tuple]] = {
    "reflow": {
        "air_temperature":     (None, 306, None, 310),
        "process_temperature": (490, 525, 485, 530),
        "rotational_speed":    (500, 1400, 400, 1600),
        "torque":              (None, 28, None, 35),
        "tool_wear":           (None, 200, None, 240),
    },
    "wave": {
        "air_temperature":     (None, 306, None, 310),
        "process_temperature": (515, 536, 510, 540),
        "rotational_speed":    (700, 1700, 600, 1800),
        "torque":              (None, 40, None, 48),
        "tool_wear":           (None, 200, None, 240),
    },
    "pickplace": {
        "air_temperature":     (None, 305, None, 310),
        "process_temperature": (None, 315, None, 320),
        "rotational_speed":    (None, 2400, None, 2600),
        "torque":              (None, 18, None, 22),
        "tool_wear":           (None, 180, None, 220),
    },
    "_default": {
        "air_temperature":     (None, 305, None, 310),
        "process_temperature": (None, 315, None, 320),
        "rotational_speed":    (None, 1700, None, 2000),
        "torque":              (None, 60, None, 75),
        "tool_wear":           (None, 200, None, 250),
    },
}


def _resolve_threshold_category(machine_type: str, machine_name: str) -> str:
    """Map machine type/name (FR or EN) to a threshold category key."""
    haystack = f"{machine_type} {machine_name}".lower()
    if "reflow" in haystack or "refusion" in haystack or "four" in haystack:
        return "reflow"
    if "wave" in haystack or "vague" in haystack or "brassage" in haystack:
        return "wave"
    if "pick" in haystack or "pose" in haystack or "place" in haystack:
        return "pickplace"
    return "_default"


def _sensor_status(value: float, th: tuple) -> str:
    """NORMAL / ATTENTION / CRITIQUE from (warn_lo, warn_hi, crit_lo, crit_hi)."""
    warn_lo, warn_hi, crit_lo, crit_hi = th
    if (crit_lo is not None and value < crit_lo) or value > crit_hi:
        return "CRITIQUE"
    if (warn_lo is not None and value < warn_lo) or value > warn_hi:
        return "ATTENTION"
    return "NORMAL"


# Plain labels + units per sensor (FR, operator-facing). Temps reported in °C.
_SENSOR_META = [
    ("air_temperature",     "Température air",     "°C",     True),
    ("process_temperature", "Température procédé", "°C",     True),
    ("rotational_speed",    "Vitesse rotation",    "tr/min", False),
    ("torque",              "Couple",              "Nm",     False),
    ("tool_wear",           "Usure outil",         "min",    False),
]


def build_sensor_status(machine_type: str, machine_name: str, readings: dict) -> list:
    """Per-sensor NORMAL/ATTENTION/CRITIQUE with display value + safe target.

    Temps converted K→°C. Single source of truth for the frontend 'Why?' panels.
    Never raises; sensors with no reading are omitted.
    """
    category = _resolve_threshold_category(machine_type or "", machine_name or "")
    thresholds = _SENSOR_THRESHOLDS[category]
    out = []
    for key, label, unit, is_temp in _SENSOR_META:
        v = readings.get(key)
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        th = thresholds[key]              # (warn_lo, warn_hi, crit_lo, crit_hi)
        status = _sensor_status(fv, th)
        warn_hi = th[1]
        if is_temp:
            value = round(fv - 273.15, 1)
            target = round(warn_hi - 273.15, 2) if warn_hi is not None else None
        else:
            value = round(fv, 1)
            target = warn_hi
        out.append({"key": key, "label": label, "value": value,
                    "unit": unit, "status": status, "target": target})
    return out


def build_ml_context(snapshot: Optional[Dict]) -> str:
    """
    Format a live ML snapshot (from modules.ml.services.chat_context.get_ml_snapshot)
    into an [ETAT ML EN TEMPS REEL] French section. Empty string if no snapshot.
    Kept concise (~300 tokens) — only actionable fields.
    """
    if not snapshot:
        return ""

    name = snapshot.get("machine_name") or "(inconnue)"
    category = _resolve_threshold_category(
        snapshot.get("machine_type") or "", name
    )
    thresholds = _SENSOR_THRESHOLDS[category]

    def num(key, fmt, suffix=""):
        v = snapshot.get(key)
        return f"{format(v, fmt)}{suffix}" if v is not None else "N/D"

    lines = [
        f"[ETAT ML EN TEMPS REEL] Machine: {name}",
        f"Score sante unifie: {num('health_score', '.0f', '/100')}"
        + (f"  |  Verdict: {snapshot['dst_verdict']}" if snapshot.get("dst_verdict") else ""),
        f"Probabilite de defaillance: {num('failure_probability', '.1f', '%')}"
        + f"  |  Niveau de risque: {snapshot.get('risk_level') or 'N/D'}",
        f"Duree de vie restante estimee (RUL): {num('rul_days', '.0f', ' jours')}",
    ]

    if snapshot.get("p6_schedule_days") is not None:
        lines.append(f"Prochaine maintenance recommandee: dans {snapshot['p6_schedule_days']:.0f} jours")
    if snapshot.get("predicted_priority"):
        lines.append(f"Priorite predite: {snapshot['predicted_priority']}")

    anom_score = snapshot.get("p4_anomaly_score") or 0.0
    if snapshot.get("is_anomaly") or anom_score > 0.5:
        lines.append(f"ANOMALIE COMPORTEMENTALE DETECTEE (score: {anom_score:.2f})")

    if snapshot.get("parts_readiness"):
        lines.append(f"Disponibilite pieces: {snapshot['parts_readiness']}")
    parts_items = snapshot.get("parts_items") or []
    shortfalls = [p for p in parts_items if p.get("shortfall", 0) > 0]
    if shortfalls:
        refs = ", ".join(str(p.get("reference", "?")) for p in shortfalls[:3])
        lines.append(f"Pieces en deficit prevu: {refs}")

    # Sensor readings with NORMAL/ATTENTION/CRITIQUE status
    sensor_defs = [
        ("Temperature air",     "air_temperature",     "K",      True),
        ("Temperature process", "process_temperature",  "K",      True),
        ("Vitesse rotation",    "rotational_speed",     "tr/min", False),
        ("Couple",              "torque",               "Nm",     False),
        ("Usure outil",         "tool_wear",            "min",    False),
    ]
    sensor_lines = []
    for label, key, unit, is_temp in sensor_defs:
        v = snapshot.get(key)
        if v is None:
            continue
        status = _sensor_status(float(v), thresholds[key])
        if is_temp:
            sensor_lines.append(f"  {label}: {float(v) - 273.15:.1f}C ({float(v):.0f} {unit}) -> {status}")
        else:
            sensor_lines.append(f"  {label}: {v} {unit} -> {status}")
    if sensor_lines:
        lines.append("Capteurs (derniere mesure):")
        lines.extend(sensor_lines)

    lines.append("[FIN ETAT ML]")
    return "\n".join(lines)


def build_full_system_prompt(
    role: str,
    user_name: str = "User",
    memories: Optional[List[Any]] = None,
    rag_chunks: Optional[List[Any]] = None,
) -> str:
    """
    Combine role-based prompt with memory context and optional RAG document context.

    Args:
        role: User role
        user_name: User's display name
        memories: Optional list of AIMemories ORM objects
        rag_chunks: Optional list of retrieved document chunks from RAG service

    Returns:
        Full system prompt string
    """
    base = get_system_prompt(role, user_name)
    if memories:
        memory_section = build_memory_context(memories)
        if memory_section:
            base = base + memory_section
    if rag_chunks:
        rag_section = build_rag_context(rag_chunks)
        if rag_section:
            base = base + rag_section
    return base


def format_tool_result(tool_name: str, result: ToolResult, max_items: int = 100) -> str:
    """
    Format tool execution results for LLM context injection.
    Truncates large result sets and handles empty results explicitly.

    Args:
        tool_name: Name of the tool called
        result: Raw tool result (list of dicts or error dict)
        max_items: Max items to include (avoids token bloat)

    Returns:
        Formatted string for injection into messages
    """
    if isinstance(result, dict) and "error" in result:
        return f"[{tool_name}] Erreur: {result['error']}"

    if not result:
        return f"[{tool_name}] Aucun resultat trouve. Informe l'utilisateur qu'il n'y a pas de donnees correspondantes."

    if isinstance(result, list):
        total = len(result)
        truncated = result[:max_items]
        try:
            data_str = json.dumps(truncated, ensure_ascii=False, default=str)
        except Exception:
            data_str = str(truncated)

        suffix = f"\n(... et {total - max_items} autres)" if total > max_items else ""
        return f"[{tool_name}] {total} resultat(s) trouve(s):\n{data_str}{suffix}"

    try:
        return f"[{tool_name}] {json.dumps(result, ensure_ascii=False, default=str)}"
    except Exception:
        return f"[{tool_name}] {str(result)}"


def format_response_for_user(data: List[dict], format_type: str = "auto") -> str:
    """
    Format data for user-friendly display.

    Args:
        data: List of data records
        format_type: auto, table, list, or summary

    Returns:
        Formatted string
    """
    if not data:
        return "Aucune donnee trouvee."

    if len(data) == 1:
        item = data[0]
        lines = [f"**{item.get('titre', item.get('nom', 'Element'))}**"]
        for k, v in item.items():
            if k not in ("id",):
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    # Multiple items — show summary
    lines = [f"**{len(data)} resultats:**"]
    for item in data[:10]:
        name = (
            item.get("titre")
            or item.get("nom")
            or item.get("message")
            or f"ID {item.get('id')}"
        )
        status = item.get("statut") or item.get("priorite") or item.get("zone", "")
        lines.append(f"- {name} [{status}]")

    if len(data) > 10:
        lines.append(f"... et {len(data) - 10} autres")

    return "\n".join(lines)
