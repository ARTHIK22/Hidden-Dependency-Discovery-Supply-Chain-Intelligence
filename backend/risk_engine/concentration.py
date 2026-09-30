from collections import Counter

from graph.graph_builder import Graph


def supplier_concentration(graph: Graph) -> list[dict]:
    supplier_buyers: dict[str, set[str]] = {}
    all_buyers: set[str] = set()
    for edge in graph.edges:
        if edge.relationship_type == "SUPPLIES":
            supplier_buyers.setdefault(edge.source, set()).add(edge.target)
            all_buyers.add(edge.target)
    total = len(all_buyers)
    return [
        {"category": "supplier_concentration", "entity_id": supplier, "affected_entities": sorted(buyers), "score": round(len(buyers) / total, 4) if total else 0.0, "severity": "high" if len(buyers) / total >= 0.5 else "medium", "explanation": f"{len(buyers)} of {total} represented buyers rely on this supplier."}
        for supplier, buyers in sorted(supplier_buyers.items()) if total and len(buyers) > 1
    ]
