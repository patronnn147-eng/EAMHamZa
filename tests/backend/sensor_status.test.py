from services.ai_prompts import build_sensor_status


def test_temp_sensor_converted_to_celsius_and_flagged():
    # pickplace process_temperature warn_hi=315K crit_hi=320K
    rows = build_sensor_status("pickplace", "PickPlace-1", {
        "process_temperature": 318.15,  # 45.0 C, between warn and crit -> ATTENTION
        "torque": 10,                    # below warn_hi 18 -> NORMAL
    })
    proc = next(r for r in rows if r["key"] == "process_temperature")
    assert proc["unit"] == "°C"
    assert proc["value"] == 45.0
    assert proc["target"] == 41.85  # 315 - 273.15
    assert proc["status"] == "ATTENTION"
    torque = next(r for r in rows if r["key"] == "torque")
    assert torque["status"] == "NORMAL"
    assert torque["unit"] == "Nm"


def test_missing_readings_are_skipped_and_never_raises():
    rows = build_sensor_status("", "", {"torque": None})
    assert rows == []


def test_critique_when_above_crit_hi():
    rows = build_sensor_status("pickplace", "x", {"process_temperature": 600.0})
    proc = next(r for r in rows if r["key"] == "process_temperature")
    assert proc["status"] == "CRITIQUE"
