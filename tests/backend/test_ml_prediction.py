import os
import joblib
import unittest

class TestMLPrediction(unittest.TestCase):
    def setUp(self):
        # Load the trained model from the backend module directory
        model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'backend', 'modules', 'ml', 'basic_machine_model.pkl')
        self.model = joblib.load(model_path)

    def test_model_exists(self):
        self.assertIsNotNone(self.model, "Model should be loaded successfully")

    def test_failure_probability_range(self):
        # Use a sample feature vector (same order as training)
        sample_features = [300.0, 310.0, 1500.0, 40.0, 5.0]
        prob = self.model.predict_proba([sample_features])[0, 1] * 100
        self.assertGreaterEqual(prob, 0)
        self.assertLessEqual(prob, 100)

if __name__ == '__main__':
    unittest.main()
