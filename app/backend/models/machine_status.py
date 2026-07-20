"""Shared machine-status vocabulary.

Single source of truth for both Machines.statut (the card badge) and
OrdresIntervention.machine_status_after (what a technician selects when
completing a work order) — same 5 values everywhere, no mapping table.
Both columns stay plain unconstrained strings; validation lives here.
"""

MACHINE_STATUSES = [
    "OPERATIONNELLE",
    "FONCTIONNEMENT_RESTREINT",
    "EN_MAINTENANCE",
    "EN_PANNE",
    "HORS_SERVICE",
]


def is_valid_machine_status(value: str) -> bool:
    return value in MACHINE_STATUSES
