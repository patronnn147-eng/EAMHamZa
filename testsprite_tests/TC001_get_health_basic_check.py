import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_get_health_basic_check():
    url = f"{BASE_URL}/health"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    json_data = response.json()
    assert isinstance(json_data, dict), "Response is not a JSON object"
    assert "status" in json_data, "Response JSON missing 'status' key"
    assert json_data["status"] == "ok", f"Expected status 'ok', got '{json_data['status']}'"

test_get_health_basic_check()