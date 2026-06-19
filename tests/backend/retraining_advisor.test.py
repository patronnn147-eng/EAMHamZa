from modules.ml.services.retraining_advisor import recommend_retraining


def test_recommends_on_enough_data():
    r = recommend_retraining(60, "stable", min_points=50)
    assert r["recommended"] and r["reasons"]


def test_recommends_on_drift():
    r = recommend_retraining(0, "drifting")
    assert r["recommended"]


def test_no_recommendation_when_quiet():
    r = recommend_retraining(3, "stable")
    assert not r["recommended"] and r["reasons"] == []
