import requests

def test_post_api_v1_ml_retrain_trigger():
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/v1/ml/retrain"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "status" in data and isinstance(data["status"], str), "Response JSON missing 'status' or not a string"
    assert "message" in data and isinstance(data["message"], str), "Response JSON missing 'message' or not a string"

test_post_api_v1_ml_retrain_trigger()