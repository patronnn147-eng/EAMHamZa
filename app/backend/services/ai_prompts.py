"""System prompt templates for AI chat"""
from typing import Dict, List, Any


def get_system_prompt(role: str, user_name: str = "User") -> str:
    """
    Generate system prompt based on user role.
    
    Args:
        role: User role (ADMIN, CHEFTECH, CHETOP, TECHNICIEN)
        user_name: User's name for personalization
    
    Returns:
        System prompt string
    """
    
    base_prompt = f"""Tu es un assistant IA pour le systeme de gestion d'actifs industriels (EAMS).
Tu reponds en francais de maniere claire et concise.
Ta mission est d'aider les utilisateurs a trouver des informations et effectuer des taches."""

    role_prompts: Dict[str, str] = {
        "ADMIN": f"""{base_prompt}

Tu as acces complet au systeme:
- Toutes les machines, tous les ordres de travail, toutes les interventions
- Plannings, alertes, analytiques
- Tu peux creer, modifier, supprimer

Utilise des formats structures pour les donnees (tableaux, listes).
Donne des informations completes incluant couts et statistiques.""",

        "CHEFTECH": f"""{base_prompt}

Tu as acces technique:
- Machines, interventions, plannings, alertes
- Ordres de travail pour ton equipe
- Analyse technique et maintenance

Sois precis sur les specifications techniques et etat des machines.""",

        "CHETOP": f"""{base_prompt}

Tu as acces production:
- Ordres de travail, demandes d'intervention
- Planning de la production
- Suivi des operations

Aide a coordonner la production et les ressources.""",

        "TECHNICIEN": f"""{base_prompt}

Tu as acces terrain:
- Tes ordres de travail assignes
- Machines qui te sont attribuees
- Interventions a realiser

Aide a prioriser les taches et trouver les informations dont tu as besoin.""",
    }

    return role_prompts.get(role, base_prompt)


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
            if k not in ('id',):
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
    
    # Multiple items - show summary
    lines = [f"**{len(data)} resultats:**"]
    for item in data[:10]:
        name = item.get('titre') or item.get('nom') or item.get('message') or f"ID {item.get('id')}"
        status = item.get('statut') or item.get('priorite') or item.get('zone', '')
        lines.append(f"- {name} [{status}]")
    
    if len(data) > 10:
        lines.append(f"... et {len(data) - 10} autres")
    
    return "\n".join(lines)