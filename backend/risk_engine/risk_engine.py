from graph.graph_builder import Graph

from risk_engine.common_dependency import analyze_common_dependencies
from risk_engine.concentration import supplier_concentration
from risk_engine.critical_dependency import identify_critical_nodes
from risk_engine.single_point_failure import analyze_single_points_of_failure


def analyze_risks(graph: Graph) -> dict:
    risks = analyze_common_dependencies(graph) + analyze_single_points_of_failure(graph) + supplier_concentration(graph)
    return {"risks": risks, "critical_nodes": identify_critical_nodes(graph), "basis": "stored relationship graph", "external_feeds_used": False}
