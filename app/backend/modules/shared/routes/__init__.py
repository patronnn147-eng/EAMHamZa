# modules/shared/routes/__init__.py
from .intervention_workflow import router  # noqa: F401
from . import (  # noqa: F401
    planning,
    planning_ordres_travail,
    ordres_travail,
    ordres_intervention,
    machines,
    dashboard,
    why,
)
