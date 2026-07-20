# modules/shared/routes/__init__.py
from .intervention_workflow import router  # noqa: F401
from . import (  # noqa: F401
    planning,
    dashboard,
    why,
)
