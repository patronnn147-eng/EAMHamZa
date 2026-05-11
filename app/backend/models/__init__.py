# Models package
 
from . import utilisateurs
from . import alertes_urgentes
from . import archives
from . import commentaires
from . import machines
from . import maintenances_planifiees
from . import notifications
from . import ordres
from . import ordres_intervention
from . import ordres_travail
from . import planning_ordres_travail
from . import planning_machines
from . import planning_utilisateurs
from . import planning_taches
from . import plannings
from . import rapports
from . import ml_prediction_log
from . import pieces
from . import piece_machine
from . import stock
from . import mouvement_stock
from . import machine_telemetry
from . import ai_memories
from .ai_memories import AIMemories
from . import chat_sessions
from .chat_sessions import ChatSession
from .machine_telemetry import MachineTelemetry
from services.audit import AuditLog  # ensure audit_logs table is created by Base.metadata
