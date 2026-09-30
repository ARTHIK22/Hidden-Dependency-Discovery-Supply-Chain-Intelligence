import pytest

from graph.graph_builder import build_graph
from risk_engine.risk_propagation import propagate_risk
from risk_engine.risk_scoring import score_risk
from risk_engine.risk_engine import analyze_risks


def test_explainable_risk_and_downstream_propagation():
    graph = build_graph([
        {"id": "s-a", "source": "supplier", "target": "company-a", "type": "SUPPLIES", "confidence": 0.9},
        {"id": "s-b", "source": "supplier", "target": "company-b", "type": "SUPPLIES", "confidence": 0.8},
        {"id": "a-p", "source": "company-a", "target": "product", "type": "DEPENDS_ON", "confidence": 0.7},
    ])
    result = analyze_risks(graph)
    assert any(item["category"] == "common_dependency" and item["entity_id"] == "supplier" for item in result["risks"])
    assert any(item["category"] == "single_point_of_failure" and item["entity_id"] == "company-a" for item in result["risks"])

    propagated = propagate_risk(graph, {"supplier": 1.0}, decay=0.8)
    assert propagated["company-a"]["score"] == 0.72
    assert propagated["product"]["score"] == 0.4032

    scored = score_risk({"concentration": 1, "uncertainty": 0.5}, {"concentration": 2, "uncertainty": 1})
    assert scored["score"] == 0.8333
    assert scored["severity"] == "high"


def test_risk_inputs_are_range_checked():
    with pytest.raises(ValueError):
        score_risk({"bad": 1.2})
    with pytest.raises(ValueError):
        propagate_risk(build_graph([]), {"entity": 1.1})
