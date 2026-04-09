import pytest
from app.backend.modules.ml.ml_predictive import MachineLearningService, get_cached_prediction, set_cached_prediction

class DummyMachine:
    def __init__(self, id=1, name="Machine1"):
        self.id = id
        self.nom = name
        self.zone = "ZoneA"
        self.sous_zone = "SubA"
        self.statut = "EN_FONCTION"
        # telemetry defaults
        self.air_temperature = 300.0
        self.process_temperature = 310.0
        self.rotational_speed = 1500
        self.torque = 40.0
        self.tool_wear = 5
        self.date_derniere_maintenance = None
        self.date_prochaine_maintenance = None

class DummyIntervention:
    def __init__(self, date_intervention=None):
        self.date_intervention = date_intervention

def test_fleet_dashboard_caching():
    machine = DummyMachine()
    interventions = []
    # First call should compute and cache
    result1 = MachineLearningService.calculate_rul(machine, interventions)
    assert isinstance(result1, dict)
    assert result1.get("machine_id") == machine.id
    # No "from_cache" flag on first result
    assert result1.get("from_cache") is None

    # Second call should hit cache
    result2 = MachineLearningService.calculate_rul(machine, interventions)
    assert isinstance(result2, dict)
    assert result2.get("from_cache") is True
    # Ensure cached result matches original output (except flag)
    for key in result1:
        if key != "from_cache":
            assert result1[key] == result2[key]
