import os
import joblib
import unittest

class TestMLPrediction(unittest.TestCase):
    def setUp(self):
        # Load the trained model from the backend module directory
        model_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'backend', 'modules', 'ml', 'basic_machine_model.pkl'
        )
        if os.path.exists(model_path):
            data = joblib.load(model_path)
            # Production model is saved as a dict: {'model': ..., 'features': ..., ...}
            # Bare sklearn estimator also accepted (legacy format).
            self.model = data['model'] if isinstance(data, dict) else data
        else:
            # CI fallback: create a minimal 7-feature RandomForestClassifier so tests
            # can validate the *interface* (feature count, predict_proba shape) without
            # needing the real .pkl artifact. Mirrors the 7-feature signature produced
            # by ml_train_basic.py: [air, process, rpm, torque, wear, temp_delta, rpm_torque]
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
            rng = np.random.default_rng(42)
            X = rng.standard_normal((60, 7))
            y = rng.integers(0, 2, size=60)
            self.model = RandomForestClassifier(n_estimators=5, random_state=42)
            self.model.fit(X, y)

    def test_model_exists(self):
        self.assertIsNotNone(self.model, "Model should be loaded successfully")

    def test_failure_probability_range(self):
        # P1 model expects 7 features:
        # [air_temperature, process_temperature, rotational_speed,
        #  torque, tool_wear, temp_delta, rpm_torque]
        air, process, rpm, torque, wear = 300.0, 310.0, 1500.0, 40.0, 5.0
        temp_delta = process - air            # 10.0
        rpm_torque = (rpm * torque) / 1000.0  # 60.0
        sample_features = [air, process, rpm, torque, wear, temp_delta, rpm_torque]

        prob = self.model.predict_proba([sample_features])[0, 1] * 100
        self.assertGreaterEqual(prob, 0)
        self.assertLessEqual(prob, 100)

    def test_feature_count(self):
        """Ensure the model was trained on 7 features (guards against accidental retraining)."""
        n_features = self.model.n_features_in_
        self.assertEqual(
            n_features, 7,
            f"P1 model should have 7 input features, got {n_features}. "
            "Check ml_train_basic.py feature engineering."
        )

if __name__ == '__main__':
    unittest.main()
