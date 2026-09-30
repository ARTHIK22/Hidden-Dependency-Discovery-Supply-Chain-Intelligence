def research_decision(*, configured_connectors: list[str], stored_evidence_count: int) -> dict:
    if configured_connectors:
        return {"action": "connector_research_available", "connectors": configured_connectors, "stored_evidence_count": stored_evidence_count}
    return {"action": "stored_data_only", "connectors": [], "stored_evidence_count": stored_evidence_count, "reason": "No external research connector is configured."}
