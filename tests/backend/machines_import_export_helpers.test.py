"""Unit tests for the pure row-validation/transform helpers in
app/backend/modules/shared/routes/machines/import_export.py."""
import io

import pandas as pd
import pytest

from modules.shared.admin_machine_standards import (
    MACHINE_STATUS_OPTIONS,
    ZONE_CMS1_NAME,
    SUBZONE_CMS_LINE1_NAME,
)
from modules.shared.routes.machines.import_export import (
    _check_name_uniqueness,
    _clean_dataframe,
    _extract_row_fields,
    _process_row,
    _read_dataframe,
    _resolve_name,
    _validate_ordre,
    _validate_row,
    _validate_zone_and_sous_zone,
)


# ── _read_dataframe ───────────────────────────────────────────────────────────

def test_read_dataframe_csv():
    contents = b"nom,zone\nM1,Z1\n"
    df = _read_dataframe(contents, "machines.csv")
    assert list(df.columns) == ["nom", "zone"]
    assert df.iloc[0]["nom"] == "M1"


def test_read_dataframe_excel():
    buf = io.BytesIO()
    pd.DataFrame({"nom": ["M1"], "zone": ["Z1"]}).to_excel(buf, index=False)
    df = _read_dataframe(buf.getvalue(), "machines.xlsx")
    assert list(df.columns) == ["nom", "zone"]


# ── _clean_dataframe ──────────────────────────────────────────────────────────

def test_clean_dataframe_normalises_columns_and_strips_whitespace():
    df = pd.DataFrame({" Nom ": ["  M1  "], "Zone": ["Z1"]})
    cleaned = _clean_dataframe(df)
    assert list(cleaned.columns) == ["nom", "zone"]
    assert cleaned.iloc[0]["nom"] == "M1"


def test_clean_dataframe_replaces_nan_with_none():
    df = pd.DataFrame({"nom": ["M1", None]})
    cleaned = _clean_dataframe(df)
    assert cleaned.iloc[1]["nom"] is None


# ── _extract_row_fields ───────────────────────────────────────────────────────

def test_extract_row_fields_finds_nom_column_case_insensitively():
    row = {"Nom Machine": "M1", "zone": "Z1", "sous_zone": "SZ1", "ordre": "3.0", "statut": "EN_PANNE"}
    raw_nom, zone, sous_zone, ordre, statut = _extract_row_fields(row)
    assert raw_nom == "M1"
    assert ordre == "3"  # ".0" stripped
    assert statut == "EN_PANNE"


def test_extract_row_fields_defaults_statut_to_operationnelle():
    row = {"zone": "Z1", "sous_zone": "", "ordre": ""}
    _, _, _, _, statut = _extract_row_fields(row)
    assert statut == "OPERATIONNELLE"


def test_extract_row_fields_none_nom_when_absent():
    row = {"zone": "Z1"}
    raw_nom, *_ = _extract_row_fields(row)
    assert raw_nom is None


# ── _validate_zone_and_sous_zone ──────────────────────────────────────────────

def test_validate_zone_missing_is_invalid():
    errors = []
    assert _validate_zone_and_sous_zone("", "", errors) is False
    assert "obligatoire" in errors[0]


def test_validate_zone_unknown_is_invalid():
    errors = []
    assert _validate_zone_and_sous_zone("NOT_A_ZONE", "", errors) is False


def test_validate_zone_valid_but_sous_zone_missing():
    errors = []
    assert _validate_zone_and_sous_zone(ZONE_CMS1_NAME, "", errors) is False


def test_validate_zone_and_sous_zone_valid():
    errors = []
    assert _validate_zone_and_sous_zone(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, errors) is True
    assert errors == []


def test_validate_zone_unknown_sous_zone_is_invalid():
    errors = []
    assert _validate_zone_and_sous_zone(ZONE_CMS1_NAME, "NOT_A_SUBZONE", errors) is False


# ── _validate_ordre ───────────────────────────────────────────────────────────

def test_validate_ordre_missing_is_invalid():
    errors = []
    assert _validate_ordre(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "", errors) is False


def test_validate_ordre_non_numeric_is_invalid():
    errors = []
    assert _validate_ordre(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "abc", errors) is False


def test_validate_ordre_out_of_range_is_invalid():
    errors = []
    assert _validate_ordre(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "999", errors) is False


def test_validate_ordre_valid():
    errors = []
    assert _validate_ordre(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "1", errors) is True
    assert errors == []


# ── _validate_row ─────────────────────────────────────────────────────────────

def test_validate_row_all_valid():
    valid, errors = _validate_row(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "1", "OPERATIONNELLE")
    assert valid is True and errors == []


def test_validate_row_invalid_statut():
    valid, errors = _validate_row(ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "1", "NOT_A_STATUS")
    assert valid is False
    assert any("Statut" in e for e in errors)


def test_validate_row_invalid_zone_short_circuits_ordre_check():
    valid, errors = _validate_row("", "", "1", "OPERATIONNELLE")
    assert valid is False
    assert len(errors) == 1  # only the zone error, ordre isn't separately checked


# ── _resolve_name ─────────────────────────────────────────────────────────────

def test_resolve_name_invalid_row_returns_raw_name_unchanged():
    name, warnings, valid, errors = _resolve_name("Whatever", ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "1", valid=False)
    assert name == "Whatever" and valid is False and warnings == [] and errors == []


def test_resolve_name_generates_when_raw_name_absent():
    name, warnings, valid, errors = _resolve_name(None, ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "1", valid=True)
    assert name  # a standardized name was generated
    assert valid is True
    assert warnings == []


def test_resolve_name_warns_when_raw_name_differs_from_generated():
    name, warnings, valid, errors = _resolve_name("Custom Name", ZONE_CMS1_NAME, SUBZONE_CMS_LINE1_NAME, "1", valid=True)
    assert warnings  # replaced with standardized name, warning issued
    assert name != "Custom Name"


# ── _check_name_uniqueness ────────────────────────────────────────────────────

def test_check_name_uniqueness_duplicate_in_db():
    errors = []
    valid = _check_name_uniqueness("M1", True, existing_names={"M1"}, file_names_seen=set(), errors=errors)
    assert valid is False
    assert "existe déjà" in errors[0]


def test_check_name_uniqueness_duplicate_in_file():
    errors = []
    seen = {"M1"}
    valid = _check_name_uniqueness("M1", True, existing_names=set(), file_names_seen=seen, errors=errors)
    assert valid is False
    assert "plusieurs fois" in errors[0]


def test_check_name_uniqueness_unique_name_adds_to_seen():
    errors = []
    seen = set()
    valid = _check_name_uniqueness("M1", True, existing_names=set(), file_names_seen=seen, errors=errors)
    assert valid is True
    assert "M1" in seen


def test_check_name_uniqueness_already_invalid_short_circuits():
    errors = []
    assert _check_name_uniqueness("M1", False, existing_names=set(), file_names_seen=set(), errors=errors) is False


# ── _process_row (integration of the above) ──────────────────────────────────

def test_process_row_valid_new_machine():
    row = pd.Series({
        "nom": None, "zone": ZONE_CMS1_NAME, "sous_zone": SUBZONE_CMS_LINE1_NAME,
        "ordre": "1", "statut": "OPERATIONNELLE", "type": "CMS", "emplacement": "Hall A",
    })
    result = _process_row(0, row, existing_names=set(), file_names_seen=set())
    assert result["row_index"] == 2
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["data"]["zone"] == ZONE_CMS1_NAME


def test_process_row_invalid_zone_reports_errors():
    row = pd.Series({"nom": "M1", "zone": "BAD_ZONE", "sous_zone": "", "ordre": "", "statut": ""})
    result = _process_row(0, row, existing_names=set(), file_names_seen=set())
    assert result["valid"] is False
    assert result["errors"]


def test_process_row_duplicate_within_file():
    existing = set()
    seen = set()
    row = pd.Series({
        "nom": None, "zone": ZONE_CMS1_NAME, "sous_zone": SUBZONE_CMS_LINE1_NAME,
        "ordre": "1", "statut": "OPERATIONNELLE",
    })
    first = _process_row(0, row, existing, seen)
    second = _process_row(1, row, existing, seen)
    assert first["valid"] is True
    assert second["valid"] is False
