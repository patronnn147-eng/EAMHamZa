"""
T7 — predict_parts_demand() tests.
Stubs load_p7 via unittest.mock.patch so no real pkl required.
"""
from unittest.mock import patch
from app.ml_microservice.src.predictions import MachineLearningService

_MOCK_PKL = {
    'failure_part_map': {
        'TWF': {
            1: {'p_used': 0.8, 'expected_qty': 1.0,
                'piece_reference': 'FC-001', 'piece_name': 'foret carbure'},
        }
    },
    'consumable_params': {
        2: {'series': [0, 2, 0, 2, 2]},
    },
    'parts_catalog': {
        1: {'piece_id': 1, 'reference': 'FC-001', 'name': 'foret carbure',
            'on_hand': 0, 'min_stock': 2, 'is_consumable': False},
        2: {'piece_id': 2, 'reference': 'OIL-001', 'name': 'huile',
            'on_hand': 5, 'min_stock': 2, 'is_consumable': True},
    },
    'meta': {'theta': 0.05, 'horizon_days': 30},
}

_PATCH = 'app.ml_microservice.src.predictions.load_p7'


def test_predict_parts_demand_returns_contract():
    with patch(_PATCH, return_value=_MOCK_PKL):
        result = MachineLearningService.predict_parts_demand(
            machine_id=1,
            rul_days=20.0,
            failure_type_probs={'TWF': 0.9},
            horizon_days=30,
        )
    assert result['source'] == 'p7_model'
    assert result['horizon_days'] == 30
    assert isinstance(result['items'], list)
    assert len(result['items']) > 0
    item = result['items'][0]
    for key in ('piece_id', 'expected_qty', 'shortfall', 'urgency_score',
                'recommended_order_qty', 'driver'):
        assert key in item, f"missing key: {key}"


def test_predict_parts_demand_fallback_when_no_pkl():
    with patch(_PATCH, return_value=None):
        result = MachineLearningService.predict_parts_demand(
            machine_id=1, rul_days=20.0,
            failure_type_probs={'TWF': 0.9}, horizon_days=30,
        )
    assert result['source'] == 'deterministic_fallback'
    assert isinstance(result['items'], list)


def test_predict_parts_demand_includes_consumable():
    with patch(_PATCH, return_value=_MOCK_PKL):
        result = MachineLearningService.predict_parts_demand(
            machine_id=1, rul_days=20.0,
            failure_type_probs={'TWF': 0.9}, horizon_days=30,
        )
    piece_ids = {i['piece_id'] for i in result['items']}
    assert 2 in piece_ids, "consumable part (Croston series) must appear in items"


def test_predict_parts_demand_zero_rul_drives_max_demand():
    """rul_days=0 → p_fail_within=1.0 → highest condition demand."""
    with patch(_PATCH, return_value=_MOCK_PKL):
        r_zero = MachineLearningService.predict_parts_demand(
            machine_id=1, rul_days=0,
            failure_type_probs={'TWF': 1.0}, horizon_days=30,
        )
        r_high = MachineLearningService.predict_parts_demand(
            machine_id=1, rul_days=10_000,
            failure_type_probs={'TWF': 1.0}, horizon_days=30,
        )
    zero_qty = next(i['expected_qty'] for i in r_zero['items'] if i['piece_id'] == 1)
    high_qty = next(i['expected_qty'] for i in r_high['items'] if i['piece_id'] == 1)
    assert zero_qty > high_qty, "zero RUL must yield higher expected qty than distant RUL"


def test_predict_parts_demand_empty_ft_probs():
    """No failure-type signal → only consumable demand."""
    with patch(_PATCH, return_value=_MOCK_PKL):
        result = MachineLearningService.predict_parts_demand(
            machine_id=1, rul_days=100.0,
            failure_type_probs={}, horizon_days=30,
        )
    piece_ids = {i['piece_id'] for i in result['items']}
    assert 1 not in piece_ids, "condition part must not appear with no FT signal"
    assert 2 in piece_ids, "consumable must still appear"
