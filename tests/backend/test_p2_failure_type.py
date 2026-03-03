import os
import joblib
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)

def test_failure_type_endpoint():
    # Sample feature values matching training columns order
    # features: [air, process, rpm, torque, wear, temp_delta]
    # temp_delta is calculated in the router
    params = {
        "air": 300.0,
        "process": 310.0,
        "rpm": 1500,
        "torque": 40.0,
        "wear": 5,
    }
    response = client.get(f"/api/v1/ml/machines/1/failure-type", params=params)
    assert response.status_code == 200
    data = response.json()
    assert "machine_id" in data and data["machine_id"] == 1
    assert "failure_types" in data
    
    failure_types = data["failure_types"]
    labels = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
    for label in labels:
        assert label in failure_types
        assert "detected" in failure_types[label]
        assert "probability" in failure_types[label]
        assert isinstance(failure_types[label]["probability"], (int, float))
        assert 0 <= failure_types[label]["probability"] <= 100
