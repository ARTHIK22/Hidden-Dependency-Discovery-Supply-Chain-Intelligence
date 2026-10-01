"""Safe JSON, CSV, and plain-text exports from persisted report records."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import json
from typing import Any, Literal

from app.models import Report


ExportFormat = Literal["json", "csv", "txt"]


@dataclass(frozen=True)
class ExportPayload:
    content: str
    media_type: str
    filename: str


def export_report(report: Report, export_format: ExportFormat) -> ExportPayload:
    report_id = str(report.id)
    data = report.structured_content or {
        "schema_version": "legacy-report-v1",
        "investigation_id": str(report.investigation_id),
        "title": report.title,
        "generated_at": report.created_at.isoformat(),
        "content": report.content,
        "demo_only": "DEMO" in report.title.upper(),
    }
    if export_format == "txt":
        return ExportPayload(report.content, "text/plain; charset=utf-8", f"report-{report_id}.txt")
    if export_format == "json":
        return ExportPayload(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            "application/json; charset=utf-8",
            f"report-{report_id}.json",
        )
    if export_format == "csv":
        return ExportPayload(_to_csv(data), "text/csv; charset=utf-8", f"report-{report_id}.csv")
    raise ValueError("Unsupported report export format")


def _to_csv(data: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "record_type", "id", "name", "relationship_type", "status", "confidence",
        "risk_score", "reason", "evidence_ids", "source", "source_url", "created_at", "demo_only",
    ])
    investigation = data.get("investigation", {})
    if isinstance(investigation, dict):
        writer.writerow([
            "investigation", investigation.get("id"), _safe(investigation.get("name")), "",
            investigation.get("status"), "", "", _safe(investigation.get("goal")), "", "", "",
            investigation.get("created_at"), data.get("demo_only", False),
        ])
    for entity in data.get("entities", []):
        writer.writerow(["entity", entity.get("id"), _safe(entity.get("name")), "", "", "", "", _safe(entity.get("description")), "", "", "", "", entity.get("demo_only", False)])
    for relation in data.get("relationships", []):
        writer.writerow([
            "relationship", relation.get("id"), _safe(f"{relation.get('source_entity')} → {relation.get('target_entity')}"),
            _safe(relation.get("relationship_type")), relation.get("verification_status"), relation.get("confidence"),
            "", _safe(relation.get("evidence_summary")), _join_ids(_verification_evidence_ids(relation)), "", "", "", relation.get("demo_only", False),
        ])
    for evidence in data.get("evidence", []):
        writer.writerow([
            "evidence", evidence.get("id"), _safe(evidence.get("title")), "", evidence.get("verification_status"),
            evidence.get("confidence"), "", _safe(evidence.get("excerpt")), "", _safe(evidence.get("source")),
            _safe(evidence.get("source_url")), evidence.get("captured_at"), evidence.get("demo_only", False),
        ])
    risk = data.get("risk", {})
    for assessment in risk.get("assessments", []):
        writer.writerow([
            f"{assessment.get('target_type', 'risk')}_risk", assessment.get("target_id"), "", "", assessment.get("level"), "",
            assessment.get("score"), _safe(assessment.get("reason")), "", "", "", risk.get("calculated_at"), data.get("demo_only", False),
        ])
    for alert in data.get("alerts", []):
        writer.writerow([
            "alert", alert.get("id"), _safe(alert.get("title")), alert.get("type"), alert.get("severity"), "",
            alert.get("risk_score"), _safe(alert.get("reason") or alert.get("message")), _join_ids(alert.get("evidence_ids", [])),
            "", "", alert.get("created_at"), alert.get("demo_only", False),
        ])
    for item in data.get("unknowns", []):
        writer.writerow([
            "unknown", item.get("target_id") or item.get("id"), _safe(item.get("factor") or item.get("kind")), "",
            item.get("status", "UNKNOWN"), "", "", _safe(item.get("reason")), "", "", "", "", data.get("demo_only", False),
        ])
    for item in data.get("conflicts", []):
        evidence_ids = [*item.get("supporting_evidence_ids", []), *item.get("conflicting_evidence_ids", [])]
        writer.writerow([
            "conflict", item.get("relationship_id"), _safe(item.get("relationship_type")), "", "CONFLICTED", "", "",
            _safe(item.get("reason")), _join_ids(evidence_ids), "", "", "", data.get("demo_only", False),
        ])
    for source in data.get("sources", []):
        writer.writerow([
            "source", "", _safe(source.get("source")), source.get("source_type"), "", "", "",
            f"evidence_count={source.get('evidence_count', 0)}", "", _safe(source.get("source")),
            _safe(source.get("source_url")), "", source.get("demo_only", False),
        ])
    if data.get("schema_version") == "legacy-report-v1":
        writer.writerow(["report", data.get("investigation_id"), _safe(data.get("title")), "", "", "", "", _safe(data.get("content")), "", "", "", data.get("generated_at"), data.get("demo_only", False)])
    return output.getvalue()


def _verification_evidence_ids(relationship: dict[str, Any]) -> list[str]:
    return [str(item.get("id")) for item in relationship.get("evidence", []) if item.get("id")]


def _join_ids(value: Any) -> str:
    return ";".join(str(item) for item in value) if isinstance(value, list) else ""


def _safe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if stripped.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value
