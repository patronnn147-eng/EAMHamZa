import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_api_v1_ml_machines_machineid_prediction_success():
    # First, we need a valid machine_id.
    # Since no direct creation endpoint for machine is specified, 
    # we will try to find one machine ID from an endpoint if possible.
    # However, no public machine listing endpoint without auth is specified for direct machine_id access.
    # We try to use a known valid id=1 as a common assumption for test environment.
    machine_id = 1
    
    url = f"{BASE_URL}/api/v1/ml/machines/{machine_id}/prediction"
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"
    
    # Validate required response fields and types
    expected_fields = {
        "machine_id": int,
        "machine_name": str,
        "rul_days": (int, float),
        "risk_level": str,
        "failure_probability": (int, float),
        "health_score": (int, float),
        "reliability_score": (int, float),
        "is_anomaly": bool,
        "explanations": list,
    }
    
    for field, field_type in expected_fields.items():
        assert field in data, f"Missing field '{field}' in response"
        assert isinstance(data[field], field_type), f"Field '{field}' is not of type {field_type}, got {type(data[field])}"
    
    # Additional plausibility checks:
    assert data["machine_id"] == machine_id, f"Returned machine_id does not match requested id {machine_id}"

test_get_api_v1_ml_machines_machineid_prediction_success()