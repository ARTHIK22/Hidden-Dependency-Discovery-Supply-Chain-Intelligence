from graph.graph_builder import build_graph
from graph.graph_traversal import traverse
from graph.path_finder import shortest_path
from graph.dependency_analyzer import common_suppliers, direct_dependencies, indirect_dependencies, single_supplier_dependencies


def test_directed_traversal_paths_and_dependency_signals():
    graph = build_graph([
        {"id": "e1", "source": "supplier-x", "target": "company-a", "type": "SUPPLIES", "confidence": 0.9},
        {"id": "e2", "source": "supplier-x", "target": "company-b", "type": "SUPPLIES", "confidence": 0.8},
        {"id": "e3", "source": "company-a", "target": "component-c", "type": "DEPENDS_ON", "confidence": 0.7},
    ])

    assert direct_dependencies(graph, "company-a") == ["component-c"]
    assert indirect_dependencies(graph, "company-a") == [{"entity_id": "component-c", "hops": 1}]
    assert shortest_path(graph, "supplier-x", "component-c", direction="both") == ["supplier-x", "company-a", "component-c"]
    assert traverse(graph, "supplier-x", 1, "outgoing") == [("supplier-x", 0), ("company-a", 1), ("company-b", 1)]
    assert common_suppliers(graph) == [{"supplier_id": "supplier-x", "dependent_entity_ids": ["company-a", "company-b"]}]
    assert single_supplier_dependencies(graph) == [
        {"entity_id": "company-a", "only_supplier_id": "supplier-x"},
        {"entity_id": "company-b", "only_supplier_id": "supplier-x"},
    ]
