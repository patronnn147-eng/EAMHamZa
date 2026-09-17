# Models package

from . import utilisateurs  # noqa: F401
from . import alertes_urgentes  # noqa: F401
from . import archives  # noqa: F401
from . import commentaires  # noqa: F401
from . import machines  # noqa: F401
from . import maintenances_planifiees  # noqa: F401
from . import notifications  # noqa: F401
from . import ordres  # noqa: F401
from . import ordres_intervention  # noqa: F401
from . import ordres_travail  # noqa: F401
from . import planning_ordres_travail  # noqa: F401
from . import planning_machines  # noqa: F401
from . import planning_utilisateurs  # noqa: F401
from . import planning_taches  # noqa: F401
from . import plannings  # noqa: F401
from . import rapports  # noqa: F401
from . import ml_prediction_log  # noqa: F401
from . import pieces  # noqa: F401
from . import piece_machine  # noqa: F401
from . import stock  # noqa: F401
from . import mouvement_stock  # noqa: F401

# Inventory consumption workflow models — must load after pieces/mouvement_stock
from . import pending_pieces  # noqa: F401
from . import required_pieces  # noqa: F401
from . import consumed_pieces  # noqa: F401
from . import machine_telemetry  # noqa: F401
from . import quick_action_run  # noqa: F401
from . import ai_memories  # noqa: F401
from .ai_memories import AIMemories  # noqa: F401
from . import chat_sessions  # noqa: F401
from .chat_sessions import ChatSession  # noqa: F401
from .machine_telemetry import MachineTelemetry  # noqa: F401
from services.audit import AuditLog  # noqa: F401 — ensure audit_logs table is created
