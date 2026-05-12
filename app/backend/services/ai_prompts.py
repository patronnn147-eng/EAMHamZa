"""System prompt templates and context builders for AI chat."""
import json
from typing import Dict, List, Any, Optional


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


def format_tool_result(tool_name: str, result: Any, max_items: int = 10) -> str:
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
