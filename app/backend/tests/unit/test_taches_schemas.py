"""
Unit tests — Pydantic schema validation for planning taches.

Covers: PlanningTacheCreate, PlanningTacheUpdate, PlanningTachesSubmitRequest,
        PlanningTacheResponse, TaskType enum.

No database or FastAPI app required — pure Pydantic validation.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from modules.shared.routes.planning.schemas import (
    TaskType,
    PlanningTacheCreate,
    PlanningTacheUpdate,
    PlanningTachesSubmitRequest,
    PlanningTacheResponse,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def valid_create_payload(**overrides) -> dict:
    base = {
        "titre": "Diagnostic compresseur",
        "description": "Vérifier pression et joints",
        "technician_id": 5,
        "machine_id": 12,
        "task_type": "DIAGNOSTIC",
        "date_debut": "2026-01-16T08:00:00",
        "date_fin": "2026-01-16T17:00:00",
    }
    return {**base, **overrides}


# ── TaskType enum ─────────────────────────────────────────────────────────────


class TestTaskType:
    def test_diagnostic_value(self):
        assert TaskType.DIAGNOSTIC == "DIAGNOSTIC"

    def test_correction_value(self):
        assert TaskType.CORRECTION == "CORRECTION"

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**valid_create_payload(task_type="INSPECTION"))


# ── PlanningTacheCreate ───────────────────────────────────────────────────────


class TestPlanningTacheCreate:
    def test_valid_payload_parses(self):
        t = PlanningTacheCreate(**valid_create_payload())
        assert t.titre == "Diagnostic compresseur"
        assert t.task_type == TaskType.DIAGNOSTIC
        assert t.technician_id == 5
        assert t.machine_id == 12

    def test_titre_required(self):
        payload = valid_create_payload()
        del payload["titre"]
        with pytest.raises(ValidationError) as exc_info:
            PlanningTacheCreate(**payload)
        assert "titre" in str(exc_info.value)

    def test_titre_max_length_255(self):
        """titre longer than 255 chars → ValidationError."""
        payload = valid_create_payload(titre="x" * 256)
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**payload)

    def test_titre_exactly_255_chars_ok(self):
        payload = valid_create_payload(titre="x" * 255)
        t = PlanningTacheCreate(**payload)
        assert len(t.titre) == 255

    def test_description_required(self):
        payload = valid_create_payload()
        del payload["description"]
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**payload)

    def test_technician_id_required(self):
        payload = valid_create_payload()
        del payload["technician_id"]
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**payload)

    def test_machine_id_required(self):
        payload = valid_create_payload()
        del payload["machine_id"]
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**payload)

    def test_date_debut_required(self):
        payload = valid_create_payload()
        del payload["date_debut"]
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**payload)

    def test_date_fin_required(self):
        payload = valid_create_payload()
        del payload["date_fin"]
        with pytest.raises(ValidationError):
            PlanningTacheCreate(**payload)

    def test_correction_type_accepted(self):
        t = PlanningTacheCreate(**valid_create_payload(task_type="CORRECTION"))
        assert t.task_type == TaskType.CORRECTION

    def test_dates_parsed_as_datetime(self):
        t = PlanningTacheCreate(**valid_create_payload())
        assert isinstance(t.date_debut, datetime)
        assert isinstance(t.date_fin, datetime)


# ── PlanningTacheUpdate ───────────────────────────────────────────────────────


class TestPlanningTacheUpdate:
    def test_all_fields_optional(self):
        """Empty payload is valid — all fields optional for PATCH semantics."""
        u = PlanningTacheUpdate()
        assert u.titre is None
        assert u.description is None
        assert u.technician_id is None
        assert u.machine_id is None
        assert u.task_type is None
        assert u.date_debut is None
        assert u.date_fin is None

    def test_partial_update_only_titre(self):
        u = PlanningTacheUpdate(titre="Nouvelle titre")
        assert u.titre == "Nouvelle titre"
        assert u.description is None

    def test_titre_max_length_enforced(self):
        with pytest.raises(ValidationError):
            PlanningTacheUpdate(titre="x" * 256)

    def test_invalid_task_type_raises(self):
        with pytest.raises(ValidationError):
            PlanningTacheUpdate(task_type="UNKNOWN")


# ── PlanningTachesSubmitRequest ───────────────────────────────────────────────


class TestPlanningTachesSubmitRequest:
    def test_submit_defaults_to_false(self):
        req = PlanningTachesSubmitRequest(tasks=[valid_create_payload()])
        assert req.submit is False

    def test_submit_true_explicitly(self):
        req = PlanningTachesSubmitRequest(tasks=[valid_create_payload()], submit=True)
        assert req.submit is True

    def test_multiple_tasks_accepted(self):
        tasks = [
            valid_create_payload(titre="Task 1", task_type="DIAGNOSTIC"),
            valid_create_payload(titre="Task 2", task_type="CORRECTION"),
        ]
        req = PlanningTachesSubmitRequest(tasks=tasks)
        assert len(req.tasks) == 2

    def test_empty_tasks_list_accepted_by_schema(self):
        """Schema itself allows empty list — business rule (min 1 task)
        is enforced at the endpoint level, not the schema level."""
        req = PlanningTachesSubmitRequest(tasks=[])
        assert req.tasks == []

    def test_tasks_required(self):
        with pytest.raises(ValidationError):
            PlanningTachesSubmitRequest()

    def test_invalid_task_inside_list_raises(self):
        """Bad task data bubbles up as ValidationError."""
        with pytest.raises(ValidationError):
            PlanningTachesSubmitRequest(tasks=[{"titre": "X", "task_type": "INVALID"}])


# ── PlanningTacheResponse (alias mapping) ────────────────────────────────────


class TestPlanningTacheResponse:
    def test_technician_id_alias_from_technicien_id(self):
        """Response schema maps technicien_id (DB column) → technician_id (API field)."""
        data = {
            "id": 1,
            "planning_id": 10,
            "titre": "Test task",
            "description": "desc",
            "technicien_id": 5,  # ← DB column name
            "machine_id": 12,
            "task_type": "DIAGNOSTIC",
            "date_debut": "2026-01-16T08:00:00",
            "date_fin": "2026-01-16T17:00:00",
            "created_by": 3,
            "created_at": "2026-01-10T10:00:00",
        }
        resp = PlanningTacheResponse.model_validate(data)
        assert resp.technician_id == 5  # ← exposed API field name

    def test_created_by_can_be_none(self):
        data = {
            "id": 1,
            "planning_id": 10,
            "titre": "Test",
            "description": "desc",
            "technicien_id": 5,
            "machine_id": 12,
            "task_type": "CORRECTION",
            "date_debut": "2026-01-16T08:00:00",
            "date_fin": "2026-01-16T17:00:00",
            "created_by": None,
            "created_at": "2026-01-10T10:00:00",
        }
        resp = PlanningTacheResponse.model_validate(data)
        assert resp.created_by is None
