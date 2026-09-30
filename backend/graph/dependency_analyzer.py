from collections import defaultdict

from graph.graph_builder import Graph


def direct_dependencies(graph: Graph, entity_id: str, relation_types: set[str] | None = None) -> list[str]:
    edges = graph.outgoing.get(str(entity_id), [])
    return sorted({edge.target for edge in edges if relation_types is None or edge.relationship_type in relation_types})


def indirect_dependencies(graph: Graph, entity_id: str, max_depth: int = 5) -> list[dict]:
    from graph.graph_traversal import traverse
    return [{"entity_id": node, "hops": depth} for node, depth in traverse(graph, entity_id, max_depth, "outgoing") if depth > 0]


def common_suppliers(graph: Graph, relationship_type: str = "SUPPLIES") -> list[dict]:
    supplier_buyers: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.relationship_type == relationship_type.upper():
            supplier_buyers[edge.source].add(edge.target)
    return [{"supplier_id": supplier, "dependent_entity_ids": sorted(buyers)} for supplier, buyers in sorted(supplier_buyers.items()) if len(buyers) > 1]


def single_supplier_dependencies(graph: Graph, relationship_type: str = "SUPPLIES") -> list[dict]:
    buyer_suppliers: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.relationship_type == relationship_type.upper():
            buyer_suppliers[edge.target].add(edge.source)
    return [{"entity_id": buyer, "only_supplier_id": next(iter(suppliers))} for buyer, suppliers in sorted(buyer_suppliers.items()) if len(suppliers) == 1]
