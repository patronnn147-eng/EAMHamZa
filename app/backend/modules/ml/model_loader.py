import os
import joblib

# Load the trained ML models
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

_MODEL = None
_MODEL_PATH = os.path.join(MODELS_DIR, 'basic_machine_model.pkl')

def get_model():
    """Get P1 failure prediction model."""
    global _MODEL
    if _MODEL is None:
        if os.path.exists(_MODEL_PATH):
            model_data = joblib.load(_MODEL_PATH)
            # Model is stored as dict with 'model' key
            if isinstance(model_data, dict):
                _MODEL = model_data.get('model')
            else:
                _MODEL = model_data
    return _MODEL

# P2: Failure Type Model
P2_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p2_failure_type.pkl')
try:
    _ml_model_p2_data = joblib.load(P2_MODEL_PATH)
    _ml_model_p2 = _ml_model_p2_data['model']
    _p2_features = _ml_model_p2_data.get('features')
    _p2_labels   = _ml_model_p2_data.get('labels')
    print(f"[OK] P2 model loaded from {P2_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P2 model: {e}")
    _ml_model_p2 = None
    _p2_features = None
    _p2_labels   = None

# P3: RUL Estimation Model
P3_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p3_rul.pkl')
try:
    _ml_model_p3 = joblib.load(P3_MODEL_PATH)
    print(f"[OK] P3 model loaded from {P3_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P3 model: {e}")
    _ml_model_p3 = None

# P5: Work Order Priority Model
P5_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p5_priority.pkl')
try:
    _ml_model_p5_data = joblib.load(P5_MODEL_PATH)
    _ml_model_p5 = _ml_model_p5_data['model']
    _p5_labels   = _ml_model_p5_data['labels']
    print(f"[OK] P5 model loaded from {P5_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P5 model: {e}")
    _ml_model_p5 = None
    _p5_labels   = None

# P4: Anomaly Detection Model
P4_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p4_anomaly.pkl')
try:
    _ml_model_p4 = joblib.load(P4_MODEL_PATH)
    print(f"[OK] P4 model loaded from {P4_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P4 model: {e}")
    _ml_model_p4 = None

# P6: Maintenance Schedule Optimization Model
P6_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p6_schedule.pkl')
try:
    _ml_model_p6 = joblib.load(P6_MODEL_PATH)
    print(f"[OK] P6 model loaded from {P6_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P6 model: {e}")
    _ml_model_p6 = None
