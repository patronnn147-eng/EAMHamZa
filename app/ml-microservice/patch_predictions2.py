"""
Patch predictions.py: auto-derive missing features for P3/P4/P6.

P3 (RUL)          : expects 7 features — add temp_delta, rpm_torque when 5 given
P4 (Anomaly)      : expects 7 features — same
P6 (Schedule)     : expects 8 features — add rpm_torque + tool_wear_sq when 6 given

Pattern matches the existing predict_priority fix (P5 auto-derives rpm_torque).
"""

path = '/app/src/predictions.py'
content = open(path).read()
original = content

# ── P3: predict_rul ──────────────────────────────────────────────────────────
old_p3 = (
    '    # ==================== P3: RUL Estimation ====================\n'
    '    @staticmethod\n'
    '    def predict_rul(features: List[float]) -> Optional[float]:\n'
    '        """\n'
    '        Predict Remaining Useful Life using P3 XGBoost.\n'
    '        Args: [air, process, rpm, torque, wear] (5 features)\n'
    '        Returns: days until failure\n'
    '        """\n'
    '        if _ml_model_p3 is None:\n'
    '            return None\n'
    '        try:\n'
    '            pred_rul = _ml_model_p3.predict(np.array([features]))[0]\n'
    '            return float(pred_rul)\n'
    '        except Exception:\n'
    '            logger.warning("P3 RUL prediction failed", exc_info=True)\n'
    '            return None'
)
new_p3 = (
    '    # ==================== P3: RUL Estimation ====================\n'
    '    @staticmethod\n'
    '    def predict_rul(features: List[float]) -> Optional[float]:\n'
    '        """\n'
    '        Predict Remaining Useful Life using P3 XGBoost.\n'
    '        Args: [air, process, rpm, torque, wear] (5) or\n'
    '              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7)\n'
    '        Returns: days until failure\n'
    '        """\n'
    '        if _ml_model_p3 is None:\n'
    '            return None\n'
    '        try:\n'
    '            # P3 trained on 7 features. Auto-derive temp_delta + rpm_torque.\n'
    '            if len(features) == 5:\n'
    '                air, process, rpm, torque, wear = features\n'
    '                temp_delta = float(process) - float(air)\n'
    '                rpm_torque = (float(rpm) * float(torque)) / 1000.0\n'
    '                features = [air, process, rpm, torque, wear, temp_delta, rpm_torque]\n'
    '            pred_rul = _ml_model_p3.predict(np.array([features]))[0]\n'
    '            return float(pred_rul)\n'
    '        except Exception:\n'
    '            logger.warning("P3 RUL prediction failed", exc_info=True)\n'
    '            return None'
)

# ── P4: detect_anomaly ───────────────────────────────────────────────────────
old_p4 = (
    '    # ==================== P4: Anomaly Detection ====================\n'
    '    @staticmethod\n'
    '    def detect_anomaly(features: List[float]) -> tuple:\n'
    '        """\n'
    '        Detect machine anomaly using P4 Isolation Forest.\n'
    '        Args: [air, process, rpm, torque, wear] (5 features)\n'
    '        Returns: (is_anomaly: bool, anomaly_score: float)\n'
    '        """\n'
    '        if _ml_model_p4 is None:\n'
    '            return False, 0.0\n'
    '        try:\n'
    '            pred = _ml_model_p4.predict([features])[0]\n'
    '            score = _ml_model_p4.decision_function([features])[0]\n'
    '            return bool(pred == -1), float(score)\n'
    '        except Exception:\n'
    '            logger.warning("P4 anomaly detection failed", exc_info=True)\n'
    '            return False, 0.0'
)
new_p4 = (
    '    # ==================== P4: Anomaly Detection ====================\n'
    '    @staticmethod\n'
    '    def detect_anomaly(features: List[float]) -> tuple:\n'
    '        """\n'
    '        Detect machine anomaly using P4 Isolation Forest.\n'
    '        Args: [air, process, rpm, torque, wear] (5) or\n'
    '              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7)\n'
    '        Returns: (is_anomaly: bool, anomaly_score: float)\n'
    '        """\n'
    '        if _ml_model_p4 is None:\n'
    '            return False, 0.0\n'
    '        try:\n'
    '            # P4 trained on 7 features. Auto-derive temp_delta + rpm_torque.\n'
    '            if len(features) == 5:\n'
    '                air, process, rpm, torque, wear = features\n'
    '                temp_delta = float(process) - float(air)\n'
    '                rpm_torque = (float(rpm) * float(torque)) / 1000.0\n'
    '                features = [air, process, rpm, torque, wear, temp_delta, rpm_torque]\n'
    '            pred = _ml_model_p4.predict([features])[0]\n'
    '            score = _ml_model_p4.decision_function([features])[0]\n'
    '            return bool(pred == -1), float(score)\n'
    '        except Exception:\n'
    '            logger.warning("P4 anomaly detection failed", exc_info=True)\n'
    '            return False, 0.0'
)

# ── P6: predict_maintenance_schedule ─────────────────────────────────────────
old_p6 = (
    '    # ==================== P6: Maintenance Schedule ====================\n'
    '    @staticmethod\n'
    '    def predict_maintenance_schedule(features: List[float]) -> float:\n'
    '        """\n'
    '        Predict optimal days to schedule maintenance using P6.\n'
    '        Args: [air, process, rpm, torque, wear, temp_delta]\n'
    '        Returns: days\n'
    '        """\n'
    '        if _ml_model_p6 is None:\n'
    '            return 7.0\n'
    '\n'
    '        try:\n'
    '            days = _ml_model_p6.predict([features])[0]\n'
    '            return max(0.0, float(days))\n'
    '        except Exception:\n'
    '            logger.warning("P6 maintenance schedule prediction failed", exc_info=True)\n'
    '            return 7.0'
)
new_p6 = (
    '    # ==================== P6: Maintenance Schedule ====================\n'
    '    @staticmethod\n'
    '    def predict_maintenance_schedule(features: List[float]) -> float:\n'
    '        """\n'
    '        Predict optimal days to schedule maintenance using P6.\n'
    '        Args: [air, process, rpm, torque, wear, temp_delta] (6) or\n'
    '              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7) or\n'
    '              [air, process, rpm, torque, wear, temp_delta, rpm_torque, tool_wear_sq] (8)\n'
    '        Returns: days\n'
    '        """\n'
    '        if _ml_model_p6 is None:\n'
    '            return 7.0\n'
    '\n'
    '        try:\n'
    '            # P6 trained on 8 features. Auto-derive derived features.\n'
    '            if len(features) >= 5:\n'
    '                air   = float(features[0])\n'
    '                rpm   = float(features[2])\n'
    '                torque = float(features[3])\n'
    '                wear  = float(features[4])\n'
    '                temp_delta = float(features[5]) if len(features) > 5 else (float(features[1]) - air)\n'
    '                rpm_torque = float(features[6]) if len(features) > 6 else (rpm * torque) / 1000.0\n'
    '                tool_wear_sq = float(features[7]) if len(features) > 7 else wear ** 2\n'
    '                features = [air, float(features[1]), rpm, torque, wear,\n'
    '                            temp_delta, rpm_torque, tool_wear_sq]\n'
    '            days = _ml_model_p6.predict([features])[0]\n'
    '            return max(0.0, float(days))\n'
    '        except Exception:\n'
    '            logger.warning("P6 maintenance schedule prediction failed", exc_info=True)\n'
    '            return 7.0'
)

patched = content
for label, old, new in [('P3', old_p3, new_p3), ('P4', old_p4, new_p4), ('P6', old_p6, new_p6)]:
    if old in patched:
        patched = patched.replace(old, new, 1)
        print(f'{label}: patched OK')
    else:
        print(f'{label}: PATTERN NOT FOUND')
        if label == "P3":
            method_name = "rul"
        elif label == "P4":
            method_name = "anomaly"
        else:
            method_name = "maintenance_schedule"
        idx = patched.find(f'predict_{method_name}')
        if idx >= 0:
            print('  actual content around method:', repr(patched[idx:idx+300]))

if patched != original:
    open(path, 'w').write(patched)
    print('predictions.py written OK')
else:
    print('ERROR: no changes applied')
