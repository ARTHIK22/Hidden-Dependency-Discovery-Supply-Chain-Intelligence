from graph.graph_builder import Graph
from graph.dependency_analyzer import common_suppliers


def analyze_common_dependencies(graph: Graph) -> list[dict]:
    return [
        {"category": "common_dependency", "severity": "high" if len(item["dependent_entity_ids"]) >= 3 else "medium", "score": min(1.0, 0.4 + 0.15 * len(item["dependent_entity_ids"])), "entity_id": item["supplier_id"], "affected_entities": item["dependent_entity_ids"], "explanation": f"{len(item['dependent_entity_ids'])} entities have a recorded SUPPLIES relationship from this supplier."}
        for item in common_suppliers(graph)
    ]
