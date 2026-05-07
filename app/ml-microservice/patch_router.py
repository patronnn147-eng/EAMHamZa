"""
Patch router.py to handle numpy scalar serialization with pydantic + numpy 2.x.

numpy 2.x numpy.float32 / numpy.int64 / numpy.bool_ are not JSON-serializable
by pydantic. Recursively convert to Python native types before building response.
"""

path = '/app/src/router.py'
content = open(path).read()

# 1. Add numpy import + _to_python helper after the last existing import line
import_block = 'from .rate_limiter import check_rate_limit'
helper = '''from .rate_limiter import check_rate_limit

try:
    import numpy as _np
    def _to_python(obj):
        """Recursively convert numpy scalars/arrays to Python native types."""
        if isinstance(obj, dict):
            return {k: _to_python(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_python(v) for v in obj]
        if isinstance(obj, _np.integer):
            return int(obj)
        if isinstance(obj, _np.floating):
            return float(obj)
        if isinstance(obj, _np.bool_):
            return bool(obj)
        if isinstance(obj, _np.ndarray):
            return obj.tolist()
        return obj
except ImportError:
    def _to_python(obj):
        return obj'''

# 2. Patch predict-all: convert predictions before return
old_predict_all_return = (
    '        predictions = MachineLearningService.predict_all(telemetry, include_shap=data.include_shap)\n'
    '        \n'
    '        return AllPredictionsResponse(\n'
    '            success=True,\n'
    '            predictions=predictions\n'
    '        )'
)
new_predict_all_return = (
    '        predictions = MachineLearningService.predict_all(telemetry, include_shap=data.include_shap)\n'
    '        predictions = _to_python(predictions)\n'
    '        return AllPredictionsResponse(\n'
    '            success=True,\n'
    '            predictions=predictions\n'
    '        )'
)

# 3. Patch predict (P1 only): convert prediction dict
old_predict_return = (
    '        return PredictionResponse(\n'
    '            success=True,\n'
    '            prediction={\n'
    '                "failure_probability": failure_prob,\n'
    '                "risk_level": risk_level,\n'
    '                "features": features\n'
    '            }\n'
    '        )'
)
new_predict_return = (
    '        return PredictionResponse(\n'
    '            success=True,\n'
    '            prediction=_to_python({\n'
    '                "failure_probability": failure_prob,\n'
    '                "risk_level": risk_level,\n'
    '                "features": features\n'
    '            })\n'
    '        )'
)

patched = content
if import_block in patched:
    patched = patched.replace(import_block, helper, 1)
    print('import + helper: OK')
else:
    print('WARN: import block not found, helper not added')

if old_predict_all_return in patched:
    patched = patched.replace(old_predict_all_return, new_predict_all_return, 1)
    print('predict-all return: OK')
else:
    print('WARN: predict-all return pattern not found')

if old_predict_return in patched:
    patched = patched.replace(old_predict_return, new_predict_return, 1)
    print('predict return: OK')
else:
    print('WARN: predict return pattern not found')

if patched != content:
    open(path, 'w').write(patched)
    print('router.py written OK')
else:
    print('ERROR: no changes applied')
