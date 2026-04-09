import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_api_v1_health_check_database_connected():
    url = f"{BASE_URL}/api/v1/health"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    # Validate status code
    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"

    # Validate JSON response content
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "status" in data, "Response JSON missing 'status' key"
    assert data["status"] == "ok", f"Expected 'status' to be 'ok' but got '{data['status']}'"

    assert "database" in data, "Response JSON missing 'database' key"
    assert data["database"] == "connected", f"Expected 'database' to be 'connected' but got '{data['database']}'"

test_get_api_v1_health_check_database_connected()