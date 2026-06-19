# modules/shared/routes/__init__.py
from .intervention_workflow import router
from . import (
    planning,
    planning_ordres_travail,
    ordres_travail,
    ordres_intervention,
    machines,
    dashboard,
    why,
)
