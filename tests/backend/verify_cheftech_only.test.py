"""Pure, no-DB tests — verify_cheftech_only is a plain sync function; calling
it directly with a stub object bypasses FastAPI's DI, which is fine since DI
just calls the function."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

import pytest
from fastapi import HTTPException
from modules.cheftech.dependencies import verify_cheftech_only
from models.utilisateurs import UserRole


class _FakeUser:
    def __init__(self, role):
        self.role = role


def test_verify_cheftech_only_allows_cheftech():
    user = _FakeUser(UserRole.CHEFTECH)
    assert verify_cheftech_only(user) is user


def test_verify_cheftech_only_rejects_admin():
    with pytest.raises(HTTPException) as exc:
        verify_cheftech_only(_FakeUser(UserRole.ADMIN))
    assert exc.value.status_code == 403


def test_verify_cheftech_only_rejects_chetop():
    with pytest.raises(HTTPException) as exc:
        verify_cheftech_only(_FakeUser(UserRole.CHETOP))
    assert exc.value.status_code == 403


def test_verify_cheftech_only_rejects_technicien():
    with pytest.raises(HTTPException) as exc:
        verify_cheftech_only(_FakeUser(UserRole.TECHNICIEN))
    assert exc.value.status_code == 403
