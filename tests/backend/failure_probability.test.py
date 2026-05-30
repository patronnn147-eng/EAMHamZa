import os
import joblib
from fastapi.testclient import TestClient
from app.backend.main import app

# Ensure the model file exists for the test environment
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'backend', 'modules', 'ml', 'basic_machine_model.pkl')
if not os.path.exists(MODEL_PATH):
    # Create a dummy model if missing (for CI safety) – this will not affect production
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np
    dummy_X = np.random.rand(10, 5)
    dummy_y = np.random.randint(0, 2, size=10)
    dummy_model = RandomForestClassifier()
    dummy_model.fit(dummy_X, dummy_y)
    joblib.dump(dummy_model, MODEL_PATH)

client = TestClient(app)

def test_failure_probability_endpoint():
    # Sample feature values matching training columns order
    params = {
        "air": 300.0,
        "process": 310.0,
        "rpm": 1500,
        "torque": 40.0,
        "wear": 5,
    }
    response = client.get(f"/api/v1/ml/machines/1/failure-probability", params=params)
    assert response.status_code == 200
    data = response.json()
    assert "machine_id" in data and data["machine_id"] == 1
    assert "failure_probability" in data
    prob = data["failure_probability"]
    assert isinstance(prob, (int, float))
    assert 0 <= prob <= 100
