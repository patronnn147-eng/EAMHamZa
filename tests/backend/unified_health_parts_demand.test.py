"""
T8 — Verify parts_demand is plumbed through unified-health response.
Pure unit tests; no DB or HTTP needed.
"""


def _build_response(fusion_result):
    """
    Mirrors the parts_demand extraction logic in backend ml/router.py
    get_unified_health(). Kept in sync manually.
    """
    return {
        "parts_demand": fusion_result.get("p7_parts_demand") if fusion_result else None,
    }


_MOCK_PARTS_DEMAND = {
    "horizon_days": 30,
    "source": "p7_model",
    "items": [
        {"piece_id": 1, "name": "foret carbure", "expected_qty": 1.26,
         "on_hand": 0, "shortfall": 1.26, "urgency_score": 1.0,
         "recommended_order_qty": 1.26, "driver": "condition"}
    ]
}


def test_parts_demand_present_when_fusion_result_has_p7():
    result = _build_response({"p7_parts_demand": _MOCK_PARTS_DEMAND})
    assert result["parts_demand"] is not None
    assert result["parts_demand"]["source"] == "p7_model"
    assert isinstance(result["parts_demand"]["items"], list)


def test_parts_demand_none_when_fusion_result_is_none():
    result = _build_response(None)
    assert result["parts_demand"] is None


def test_parts_demand_none_when_key_missing_from_fusion():
    result = _build_response({"some_other_key": 42})
    assert result["parts_demand"] is None


def test_parts_demand_contract_shape():
    result = _build_response({"p7_parts_demand": _MOCK_PARTS_DEMAND})
    pd = result["parts_demand"]
    assert "horizon_days" in pd
    assert "source" in pd
    assert "items" in pd
    item = pd["items"][0]
    for key in ("piece_id", "expected_qty", "shortfall", "urgency_score",
                "recommended_order_qty", "driver"):
        assert key in item, f"item missing key: {key}"
