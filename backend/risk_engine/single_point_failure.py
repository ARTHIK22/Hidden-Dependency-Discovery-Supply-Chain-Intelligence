from graph.graph_builder import Graph
from graph.dependency_analyzer import single_supplier_dependencies


def analyze_single_points_of_failure(graph: Graph) -> list[dict]:
    return [
        {"category": "single_point_of_failure", "severity": "high", "score": 0.8, "entity_id": item["entity_id"], "supplier_id": item["only_supplier_id"], "affected_entities": [item["entity_id"]], "explanation": "Only one supplier is represented in the recorded relationship graph; completeness is unknown."}
        for item in single_supplier_dependencies(graph)
    ]
