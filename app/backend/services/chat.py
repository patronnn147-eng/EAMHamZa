import logging
import re
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.machines import Machines
from models.alertes import Alert
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs

logger = logging.getLogger(__name__)


INTENT_PATTERNS = {
    "list_machines": [
        r"machines?\s+in\s+(zone\s+)?(\w+)",
        r"show\s+machines?\s+in\s+(zone\s+)?(\w+)",
        r"list\s+machines?\s+in\s+(zone\s+)?(\w+)",
    ],
    "machines_by_status": [
        r"(?:machines?|assets?)\s+(?:in\s+)?(broken|maintenance|operational|active|offline|stock)",
        r"(?:show|list)\s+(?:the\s+)?(broken|maintenance|operational|active|offline|stock)\s+machines?",
    ],
    "machines_by_type": [
        r"(?:machines?|assets?)\s+of\s+type\s+(\w+)",
        r"(\w+)\s+machines?",
    ],
    "due_maintenance": [
        r"due\s+for\s+maintenance",
        r"need(s)?\s+maintenance",
        r"maintenance\s+due",
    ],
    "show_alerts": [
        r"(?:show|list|get|find)\s+alerts?",
        r"(?:show|list|get|find)\s+(?:the\s+)?(critical|high|medium|low)\s+alerts?",
    ],
    "show_work_orders": [
        r"(?:show|list|get|find)\s+(?:the\s+)?work\s+orders?",
        r"work\s+orders?\s+for\s+(\w+)",
        r"my\s+work\s+orders?",
    ],
    "work_orders_by_status": [
        r"work\s+orders?\s+(?:that\s+are\s+)?(pending|in_progress|completed|cancelled)",
    ],
    "critical_machines": [
        r"critical\s+machines?",
        r"machines?\s+(?:at\s+)?high\s+risk",
        r"urgent\s+machines?",
    ],
    "predictive_machines": [
        r"predictive\s+maintenance",
        r"low\s+RUL",
        r"(?:machines?|assets?)\s+need(?:ing)?\s+(?:predictive|preventive)",
    ],
    "expensive_repairs": [
        r"expensive\s+repairs?",
        r"high\s+cost\s+(?:repairs?|maintenance)",
        r"costly\s+(?:repairs?|maintenance)",
    ],
    "machines_needing_repair": [
        r"machines?\s+need(?:ing)?\s+repair",
        r"repair\s+(?:for|needed)",
        r"breakdown",
    ],
}


def parse_query(user_input: str) -> Dict[str, Any]:
    """
    Parse user input and extract intent and parameters.
    
    Returns:
        dict with keys: intent, params, confidence, raw_query
    """
    user_input = user_input.lower().strip()
    original_query = user_input
    
    # Check each intent pattern
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                groups = match.groups()
                params = {}
                
                if intent == "list_machines" and groups:
                    params["zone"] = groups[-1].upper() if groups[-1] else None
                elif intent == "machines_by_status" and groups:
                    status_map = {
                        "broken": "PANNE",
                        "maintenance": "MAINTENANCE",
                        "operational": "OPERATIONAL",
                        "active": "ACTIVE",
                        "offline": "Hors_service",
                        "stock": "STOCK"
                    }
                    params["status"] = status_map.get(groups[-1].lower(), groups[-1].upper())
                elif intent == "machines_by_type" and groups:
                    params["machine_type"] = groups[-1]
                elif intent == "show_alerts" and groups and groups[0]:
                    params["severity"] = groups[0].upper()
                elif intent == "work_orders_by_status" and groups:
                    status_map = {
                        "pending": "EN_ATTENTE",
                        "in_progress": "EN_COURS",
                        "completed": "TERMINE",
                        "cancelled": "ANNULE"
                    }
                    params["status"] = status_map.get(groups[-1].lower(), groups[-1].upper())
                elif intent == "show_work_orders" and "for" in user_input:
                    for m in re.finditer(r"for\s+(\w+)", user_input):
                        params["assignee"] = m.group(1)
                
                return {
                    "intent": intent,
                    "params": params,
                    "confidence": 0.9,
                    "raw_query": original_query
                }
    
    # Default fallback
    return {
        "intent": "unknown",
        "params": {},
        "confidence": 0.0,
        "raw_query": original_query
    }


async def execute_query(
    db: AsyncSession,
    intent: str,
    params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Execute the parsed query and return results."""
    
    if intent == "list_machines" or intent == "machines_by_status":
        query = select(Machines)
        if params.get("zone"):
            query = query.where(Machines.zone.ilike(f"%{params['zone']}%"))
        if params.get("status"):
            query = query.where(Machines.statut == params["status"])
        if params.get("machine_type"):
            query = query.where(Machines.type.ilike(f"%{params['machine_type']}%"))
        
        result = await db.execute(query.limit(50))
        machines = result.scalars().all()
        return [
            {
                "id": m.id,
                "name": m.nom,
                "type": m.type,
                "zone": m.zone,
                "status": m.statut
            }
            for m in machines
        ]
    
    elif intent == "due_maintenance" or intent == "machines_by_status":
        # Find machines due for maintenance
        query = select(Machines).where(Machines.statut == "MAINTENANCE")
        result = await db.execute(query.limit(50))
        machines = result.scalars().all()
        return [
            {
                "id": m.id,
                "name": m.nom,
                "type": m.type,
                "zone": m.zone,
                "status": m.statut
            }
            for m in machines
        ]
    
    elif intent == "show_alerts":
        query = select(Alert).where(Alert.is_active == True)
        if params.get("severity"):
            query = query.where(Alert.severity == params["severity"])
        
        result = await db.execute(query.limit(50))
        alerts = result.scalars().all()
        return [
            {
                "id": a.id,
                "machine_id": a.machine_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "rul_days": a.rul_days,
                "failure_probability": a.failure_probability
            }
            for a in alerts
        ]
    
    elif intent == "show_work_orders" or intent == "work_orders_by_status":
        query = select(Ordres_travail)
        if params.get("status"):
            query = query.where(Ordres_travail.statut == params["status"])
        if params.get("assignee"):
            # Try to find user
            user_query = select(Utilisateurs).where(
                Utilisateurs.nom.ilike(f"%{params['assignee']}%")
            )
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            if user:
                query = query.where(Ordres_travail.technicien_id == user.id)
        
        result = await db.execute(query.limit(50))
        wos = result.scalars().all()
        return [
            {
                "id": wo.id,
                "title": wo.titre,
                "status": wo.statut,
                "priority": wo.priorite,
                "technicien_id": wo.technicien_id
            }
            for wo in wos
        ]
    
    elif intent == "critical_machines" or intent == "predictive_machines":
        # Get alerts with high failure probability or low RUL
        query = select(Alert).where(
            Alert.is_active == True,
            Alert.failure_probability != None
        )
        result = await db.execute(query.limit(50))
        alerts = result.scalars().all()
        
        critical = [a for a in alerts if a.failure_probability and a.failure_probability > 0.5]
        return [
            {
                "id": a.id,
                "machine_id": a.machine_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "failure_probability": a.failure_probability,
                "rul_days": a.rul_days
            }
            for a in critical
        ]
    
    elif intent == "expensive_repairs":
        # Get work orders with high estimated cost
        query = select(Ordres_travail).where(
            Ordres_travail.cout_estime != None,
            Ordres_travail.cout_estime > 1000
        ).order_by(Ordres_travail.cout_estime.desc())
        
        result = await db.execute(query.limit(20))
        wos = result.scalars().all()
        return [
            {
                "id": wo.id,
                "title": wo.titre,
                "status": wo.statut,
                "estimated_cost": wo.cout_estime
            }
            for wo in wos
        ]
    
    elif intent == "machines_needing_repair":
        query = select(Machines).where(Machines.statut == "PANNE")
        result = await db.execute(query.limit(50))
        machines = result.scalars().all()
        return [
            {
                "id": m.id,
                "name": m.nom,
                "type": m.type,
                "zone": m.zone,
                "status": m.statut
            }
            for m in machines
        ]
    
    return []


def format_response(
    results: List[Dict[str, Any]],
    intent: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """Format query results for display."""
    
    intent_labels = {
        "list_machines": "Machines in Zone",
        "machines_by_status": "Machines",
        "machines_by_type": "Machines of Type",
        "due_maintenance": "Due for Maintenance",
        "show_alerts": "Active Alerts",
        "show_work_orders": "Work Orders",
        "work_orders_by_status": "Work Orders",
        "critical_machines": "Critical Machines",
        "predictive_machines": "Predictive Maintenance",
        "expensive_repairs": "High Cost Repairs",
        "machines_needing_repair": "Machines Needing Repair",
    }
    
    if not results:
        message = "No results found for your query."
        if intent == "list_machines" and params.get("zone"):
            message = f"No machines found in zone '{params['zone']}'."
    else:
        count = len(results)
        message = f"Found {count} result{'s' if count > 1 else ''}."
    
    return {
        "results": results,
        "message": message,
        "intent_label": intent_labels.get(intent, intent),
        "count": len(results)
    }


def get_suggestions(user_role: Optional[str] = None) -> List[str]:
    """Get suggested queries based on user role."""
    
    base_suggestions = [
        "Show machines in Zone A",
        "Show alerts",
        "Show critical machines",
        "Machines needing repair",
        "Show work orders",
    ]
    
    admin_suggestions = [
        "Show all machines",
        "Show high alerts",
        "Pending work orders",
        "Expensive repairs",
    ]
    
    technician_suggestions = [
        "My work orders",
        "Show alerts for my machines",
    ]
    
    suggestions = base_suggestions.copy()
    if user_role in ["ADMIN", "CHEFTECH", "CHETOP"]:
        suggestions.extend(admin_suggestions)
    if user_role == "TECHNICIEN":
        suggestions.extend(technician_suggestions)
    
    return suggestions[:10]
