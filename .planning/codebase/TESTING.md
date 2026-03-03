# Testing Patterns

**Analysis Date:** 2026-03-03

## Test Framework

### Backend (Python)

**Runner:** pytest / unittest
- Tests located in `tests/backend/`
- Uses `fastapi.testclient.TestClient` for API testing

**Run Commands:**
```bash
# Run all tests (if pytest is configured)
pytest tests/backend/

# Run specific test file
python -m pytest tests/backend/test_ml_prediction.py -v
```

### Frontend (TypeScript/React)

**Testing Framework:** Not explicitly configured
- No Vitest or Jest configuration found
- No test files in `app/frontend/src/`
- No test scripts in `package.json`

**Note:** Frontend testing infrastructure is not set up

## Test File Organization

### Backend Structure

```
tests/
└── backend/
    ├── test_p2_failure_type.py      # API endpoint tests
    ├── test_failure_probability.py  # API endpoint tests  
    └── test_ml_prediction.py        # Unit tests with unittest
```

### Naming Convention

- Test files: `test_*.py`
- Test functions: `test_*()`
- Test classes: `Test*` (unittest style)

### Frontend Structure

**Not applicable** - No test files in frontend codebase

## Test Structure

### Backend - FastAPI TestClient Pattern

```python
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)

def test_failure_type_endpoint():
    """Test the ML failure type prediction endpoint"""
    params = {
        "air": 300.0,
        "process": 310.0,
        "rpm": 1500,
        "torque": 40.0,
        "wear": 5,
    }
    response = client.get(f"/api/v1/ml/machines/1/failure-type", params=params)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "machine_id" in data
    assert "failure_types" in data
    
    # Validate response structure
    failure_types = data["failure_types"]
    labels = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
    for label in labels:
        assert label in failure_types
        assert "detected" in failure_types[label]
        assert "probability" in failure_types[label]
        assert isinstance(failure_types[label]["probability"], (int, float))
        assert 0 <= failure_types[label]["probability"] <= 100
```

### Backend - Unittest Pattern

```python
import unittest
import joblib
import os

class TestMLPrediction(unittest.TestCase):
    def setUp(self):
        """Load the trained model before each test"""
        model_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'app', 'backend', 'modules', 'ml', 
            'basic_machine_model.pkl'
        )
        self.model = joblib.load(model_path)

    def test_model_exists(self):
        """Verify model loads successfully"""
        self.assertIsNotNone(self.model, "Model should be loaded successfully")

    def test_failure_probability_range(self):
        """Test prediction probability is in valid range"""
        sample_features = [300.0, 310.0, 1500.0, 40.0, 5.0]
        prob = self.model.predict_proba([sample_features])[0, 1] * 100
        self.assertGreaterEqual(prob, 0)
        self.assertLessEqual(prob, 100)

if __name__ == '__main__':
    unittest.main()
```

## Mocking

### Backend Pattern

**Model Mocking for Tests:**
```python
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '...')
if not os.path.exists(MODEL_PATH):
    # Create dummy model if missing (for CI safety)
    dummy_X = np.random.rand(10, 5)
    dummy_y = np.random.randint(0, 2, size=10)
    dummy_model = RandomForestClassifier()
    dummy_model.fit(dummy_X, dummy_y)
    joblib.dump(dummy_model, MODEL_PATH)
```

### API Request Mocking

- Uses FastAPI's `TestClient` - handles HTTP layer mocking
- No external HTTP mocking library (e.g., `requests-mock`, `responses`) in use

### What to Mock

**Currently practiced:**
- Model files: Create dummy models if missing
- TestClient handles request/response cycle

**Not currently mocked:**
- Database connections (uses real database via TestClient)
- External services (ML models loaded from file)

## Fixtures and Factories

### Test Data

**Pattern - Inline test data:**
```python
# Sample feature values matching training columns order
params = {
    "air": 300.0,
    "process": 310.0,
    "rpm": 1500,
    "torque": 40.0,
    "wear": 5,
}
```

**Pattern - Path-based fixtures:**
```python
model_path = os.path.join(
    os.path.dirname(__file__),
    '..', '..',
    'app', 'backend', 'modules', 'ml',
    'basic_machine_model.pkl'
)
```

### Location

- Test data embedded in test files
- No dedicated fixtures directory

## Coverage

**Requirements:** None enforced

**View Coverage:** Not configured

**Current test coverage:** Minimal
- Only ML prediction endpoints tested
- No tests for:
  - Authentication/authorization
  - CRUD operations
  - Frontend components

## Test Types

### Unit Tests

**Backend:**
- `test_ml_prediction.py` - Tests ML model loading and prediction
- Focus: Model returns valid probability range

**Scope:**
- Individual functions/methods
- Model predictions

### Integration Tests

**Backend:**
- `test_p2_failure_type.py` - Tests API endpoint with full request/response cycle
- `test_failure_probability.py` - Tests API endpoint integration
- Uses FastAPI TestClient for HTTP testing

**Scope:**
- API endpoints
- Full request/response flow
- Database operations via TestClient

### E2E Tests

**Frontend:** Not used
**Backend:** Not used

## Common Patterns

### Async Testing

**FastAPI/TestClient:**
```python
# TestClient handles async automatically
def test_endpoint():
    response = client.get("/api/v1/ml/machines/1/failure-type", params=params)
    # Synchronous call, async handled internally
```

### Error Testing

**Pattern - Status code validation:**
```python
def test_error_cases():
    # Test 404
    response = client.get("/api/v1/ml/machines/999/failure-type", params=params)
    assert response.status_code == 404
```

**Pattern - Response validation:**
```python
def test_response_structure():
    response = client.get(...)
    data = response.json()
    assert "error" not in data or "machine_id" in data
```

### Test Discovery

**pytest discovery:**
- Files matching `test_*.py`
- Functions matching `test_*()`
- Classes matching `Test*`

## Gaps and Recommendations

### Frontend Testing

**Missing:**
- No test framework configured (Jest/Vitest)
- No test files
- No component testing
- No hook testing

**Recommendation:**
- Install Vitest for Vite integration
- Add React Testing Library
- Create test directory: `src/**/*.test.tsx`

### Backend Testing

**Limited coverage:**
- Only ML endpoints tested
- Missing: Auth, CRUD operations, services, models

**Recommendation:**
- Add tests for:
  - Authentication endpoints
  - All CRUD routers
  - Service layer functions
  - Edge cases and error handling

### Test Infrastructure Gaps

- No CI/CD pipeline for tests
- No coverage reporting
- No test utilities/helpers
- No fixture factories

---

*Testing analysis: 2026-03-03*
