"""Unit tests — P7 parts re-pricing matches on name, not on the model's piece_id.

The model's piece_id values come from its training database. Matching on them
against a live catalogue silently re-prices an unrelated part (failure_part_map
starts TWF at piece_id 1, which in any live catalogue is just whatever part
holds that row). These tests pin the name-based behaviour. Pure functions only —
no DB, no async, matching this repo's tests/unit convention.
"""
from modules.ml.routes.health import _normalise_part_name, _reprice_part_item


def _stock(**overrides):
    base = {
        "piece_id": 77,
        "name": "Roulement 6204",
        "reference": "BRG-6204",
        "min_stock": 10.0,
        "on_hand": 25.0,
    }
    base.update(overrides)
    return {_normalise_part_name(base["name"]): base}


# ── name normalisation ────────────────────────────────────────────────────────


def test_normalise_folds_case_accents_and_spacing():
    assert _normalise_part_name("Condensateur De Démarrage") == "condensateur de demarrage"
    assert _normalise_part_name("  ACCOUPLEMENT   élastique ") == "accouplement elastique"


def test_normalise_handles_empty_and_none_safely():
    assert _normalise_part_name("") == ""
    assert _normalise_part_name(None) == ""


def test_accented_and_unaccented_spellings_collide():
    """The whole point: "élastomère" typed either way must match one catalogue row."""
    assert _normalise_part_name("Insert élastomère") == _normalise_part_name("insert elastomere")


# ── re-pricing ────────────────────────────────────────────────────────────────


def test_matching_part_is_repriced_against_live_stock():
    item = {"piece_id": 1, "name": "roulement 6204", "expected_qty": 4.0,
            "on_hand": 0.0, "shortfall": 4.0, "urgency_score": 1.0}
    assert _reprice_part_item(item, _stock(), horizon=30) is True
    assert item["on_hand"] == 25.0
    assert item["shortfall"] == 0.0       # 25 on hand covers demand of 4
    assert item["urgency_score"] == 0.0
    assert item["name"] == "Roulement 6204"


def test_matched_item_is_repointed_at_the_live_piece_id():
    """Downstream procurement acts on piece_id — it must be the live row, not
    the model's training-DB id."""
    item = {"piece_id": 1, "name": "roulement 6204", "expected_qty": 4.0}
    _reprice_part_item(item, _stock(piece_id=77), horizon=30)
    assert item["piece_id"] == 77


def test_uncatalogued_part_is_left_untouched():
    """A part the site genuinely doesn't stock keeps its zeros — inventing
    stock for it would be worse than reporting none."""
    item = {"piece_id": 28, "name": "grille de protection", "expected_qty": 0.1,
            "on_hand": 0.0, "shortfall": 0.1, "urgency_score": 1.0}
    assert _reprice_part_item(item, _stock(), horizon=30) is False
    assert item["on_hand"] == 0.0
    assert item["urgency_score"] == 1.0
    assert item["piece_id"] == 28


def test_colliding_piece_id_does_not_reprice_an_unrelated_part():
    """Regression guard for the original bug: model piece_id 1 must NOT pick up
    the live catalogue's row 1 when the names describe different parts."""
    live = _stock(piece_id=1, name="Roulement 6204", on_hand=25.0)
    item = {"piece_id": 1, "name": "tête de perçage complète", "expected_qty": 2.0,
            "on_hand": 0.0, "shortfall": 2.0, "urgency_score": 1.0}
    assert _reprice_part_item(item, live, horizon=30) is False
    assert item["name"] == "tête de perçage complète"
    assert item["on_hand"] == 0.0


def test_shortfall_and_order_respect_min_stock():
    item = {"piece_id": 1, "name": "roulement 6204", "expected_qty": 2.0}
    _reprice_part_item(item, _stock(on_hand=3.0, min_stock=10.0), horizon=30)
    assert item["shortfall"] == 0.0            # 3 on hand covers demand of 2
    assert item["recommended_order_qty"] == 7.0  # but min_stock 10 - 3 on hand
