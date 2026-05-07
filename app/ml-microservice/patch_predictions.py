"""One-shot patch: add rpm_torque auto-derivation to predict_priority."""
import re

path = '/app/src/predictions.py'
content = open(path).read()

old = (
    '    # ==================== P5: Work Order Priority ====================\n'
    '    @staticmethod\n'
    '    def predict_priority(features: List[float]) -> str:\n'
    '        """\n'
    '        Predict work order priority level using P5 model.\n'
    '        Args: [air, process, rpm, torque, wear, temp_delta]\n'
    '        Returns: priority level\n'
    '        """\n'
    '        if _ml_model_p5 is None:\n'
    '            return "Medium"\n'
    '\n'
    '        try:\n'
    '            pred_idx = _ml_model_p5.predict([features])[0]\n'
    '            return _p5_labels[pred_idx]\n'
    '        except Exception:\n'
    '            logger.warning("P5 priority prediction failed", exc_info=True)\n'
    '            return "Medium"'
)

new = (
    '    # ==================== P5: Work Order Priority ====================\n'
    '    @staticmethod\n'
    '    def predict_priority(features: List[float]) -> str:\n'
    '        """\n'
    '        Predict work order priority level using P5 model.\n'
    '        Args: [air, process, rpm, torque, wear, temp_delta] (6 features) OR\n'
    '              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)\n'
    '        Returns: priority level string\n'
    '        """\n'
    '        if _ml_model_p5 is None:\n'
    '            return "Medium"\n'
    '\n'
    '        try:\n'
    '            # P5 model trained on 7 features. Auto-derive rpm_torque when\n'
    '            # caller provides 6 so both call-sites work without shape errors.\n'
    '            if len(features) == 6:\n'
    '                rpm_torque = (float(features[2]) * float(features[3])) / 1000.0\n'
    '                features = list(features) + [rpm_torque]\n'
    '            pred_idx = _ml_model_p5.predict([features])[0]\n'
    '            return _p5_labels[pred_idx]\n'
    '        except Exception:\n'
    '            logger.warning("P5 priority prediction failed", exc_info=True)\n'
    '            return "Medium"'
)

if old in content:
    patched = content.replace(old, new, 1)
    open(path, 'w').write(patched)
    print('predictions.py patched OK')
else:
    print('PATTERN NOT FOUND - checking actual content...')
    idx = content.find('predict_priority')
    print(repr(content[idx:idx+600]))
