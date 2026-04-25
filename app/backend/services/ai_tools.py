"""Tool definitions for Groq function calling."""
from typing import Dict, List, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.models.machines import Machines
from app.backend.models.ordres_travail import Ordres_travail
from app.backend.models.ordres_intervention import Ordres_intervention
from app.backend.models.plannings import Plannings
from app.backend.models.alertes import Alert


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Return tool definitions for Groq LLM.
    These define what actions the AI can take.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_machines",
                "description": "Search for machines by zone, status, or type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "zone": {"type": "string", "description": "Zone name (e.g., Zone_Nord, Zone_Sud, Zone_Centre)"},
                        "status": {"type": "string", "description": "Machine status (OPERATIONNELLE, MAINTENANCE, PANNE)"},
                        "machine_type": {"type": "string", "description": "Machine type"},
                    },
                    "required": [],
                },
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "get_work_orders",
                "description": "Get work orders with optional filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Order status (EN_ATTENTE, EN_COURS, TERMINÉ, ANNULÉ)"},
                        "utilisateur_id": {"type": "integer", "description": "Filter by user ID"},
                        "machine_id": {"type": "integer", "description": "Filter by machine ID"},
                    },
                    "required": [],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_interventions",
                "description": "Get maintenance interventions with optional filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "machine_id": {"type": "integer", "description": "Filter by machine ID"},
                        "statut": {"type": "string", "description": "Intervention status (EN_ATTENTE, EN_COURS, TERMINÉE)"},
                    },
                    "required": [],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_plannings",
                "description": "Get planning schedule for date range",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string", "description": "Start date (ISO format, e.g., 2024-01-01)"},
                        "date_to": {"type": "string", "description": "End date (ISO format, e.g., 2024-12-31)"},
                    },
                    "required": [],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_alerts",
                "description": "Get active system alerts",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "priorite": {"type": "string", "description": "Priority level (LOW, MEDIUM, HIGH, CRITICAL)"},
                        "machine_id": {"type": "integer", "description": "Filter by machine ID"},
                    },
                    "required": [],
                },
            }
        },
    ]


def execute_tool(name: str, arguments: dict, db: Session) -> Any:
    """
    Execute a tool call and return results.
    
    Args:
        name: Tool name (function name)
        arguments: Tool arguments
        db: Database session
    
    Returns:
        Tool execution results
    """
    if name == "search_machines":
        query = select(Machines)
        if arguments.get("zone"):
            query = query.where(Machines.zone == arguments["zone"])
        if arguments.get("status"):
            query = query.where(Machines.statut == arguments["status"])
        if arguments.get("machine_type"):
            query = query.where(Machines.type == arguments["machine_type"])
        result = db.execute(query)
        return [{"id": m.id, "nom": m.nom, "zone": m.zone, "statut": m.statut, "type": m.type} for m in result.scalars().all()]
    
    elif name == "get_work_orders":
        query = select(Ordres_travail)
        if arguments.get("status"):
            query = query.where(Ordres_travail.statut == arguments["status"])
        if arguments.get("utilisateur_id"):
            query = query.where(Ordres_travail.utilisateur_id == arguments["utilisateur_id"])
        if arguments.get("machine_id"):
            query = query.where(Ordres_travail.machine_id == arguments["machine_id"])
        result = db.execute(query.limit(50))
        return [{"id": o.id, "titre": o.titre, "statut": o.statut, "priorite": o.priorite, "machine_id": o.machine_id} for o in result.scalars().all()]
    
    elif name == "get_interventions":
        query = select(Ordres_intervention)
        if arguments.get("machine_id"):
            query = query.where(Ordres_intervention.machine_id == arguments["machine_id"])
        if arguments.get("statut"):
            query = query.where(Ordres_intervention.statut == arguments["statut"])
        result = db.execute(query.limit(50))
        return [{"id": i.id, "machine_id": i.machine_id, "statut": i.statut, "problem_description": i.problem_description} for i in result.scalars().all()]
    
    elif name == "get_plannings":
        query = select(Plannings)
        result = db.execute(query.limit(50))
        return [{"id": p.id, "identifiant_planning": p.identifiant_planning, "date_debut": str(p.date_debut), "date_fin": str(p.date_fin), "type": str(p.type)} for p in result.scalars().all()]
    
    elif name == "get_alerts":
        query = select(Alert).where(Alert.is_active == True)
        if arguments.get("priorite"):
            query = query.where(Alert.priority == arguments["priorite"])
        if arguments.get("machine_id"):
            query = query.where(Alert.machine_id == arguments["machine_id"])
        result = db.execute(query.limit(20))
        return [{"id": a.id, "machine_id": a.machine_id, "message": a.message, "priority": a.priority, "severity": str(a.severity)} for a in result.scalars().all()]
    
    return {"error": f"Unknown tool: {name}"}