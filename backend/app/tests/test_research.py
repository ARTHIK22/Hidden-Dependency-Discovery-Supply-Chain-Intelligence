from collections.abc import Generator
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base, Entity, Evidence, Investigation, Relationship
from app.research.models import ResearchBatch, ResearchQuery, ResearchResult
from app.research.provider import ResearchProvider, UnconfiguredResearchProvider, validate_fetch_url
from app.services.research_service import (
    ResearchExecutionError,
    ResearchNotReadyError,
    execute_research,
    start_research,
)


@pytest.fixture()
def harness(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "jwt_secret_key", "research-test-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr("app.api.v1.investigations.get_engine", lambda: engine)
    app.state.research_test_session_factory = factory
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        del app.state.research_test_session_factory
        engine.dispose()


def _auth(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Research Tester",
            "email": f"{uuid4()}@example.test",
            "password": "research-test-password",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_planned(client: TestClient, headers: dict[str, str], depth: str = "deep") -> str:
    response = client.post(
        "/api/investigations",
        headers=headers,
        json={"goal": "Find hidden lithium dependencies behind Acme Electronics", "depth": depth},
    )
    assert response.status_code == 201
    return response.json()["investigation"]["id"]


class DeterministicProvider(ResearchProvider):
    name = "deterministic_test_provider"
    mode = "external"

    def __init__(self, content: str = "Supplier B supplies Acme Electronics.") -> None:
        self.content = content
        self.queries: list[str] = []

    def search(self, query: ResearchQuery) -> ResearchBatch:
        self.queries.append(query.query)
        result = ResearchResult.model_validate(
            {
                "query": query.query,
                "source_url": "https://research.example.test/source/one",
                "source_title": "Supplier B disclosure",
                "source_domain": "research.example.test",
                "retrieved_at": datetime.now(timezone.utc),
                "content": self.content,
                "relevance": 0.8,
                "research_step": query.purpose,
                "provider": self.name,
                "source_type": "web_search",
                "metadata": {"fixture": True},
            }
        )
        return ResearchBatch(query=query, results=[result])

    def fetch(self, url: str, query: ResearchQuery) -> ResearchResult:
        validate_fetch_url(url)
        return self.search(query).results[0]


class FailingProvider(DeterministicProvider):
    def search(self, query: ResearchQuery) -> ResearchBatch:
        raise RuntimeError("private test failure detail")


class SlowProvider(DeterministicProvider):
    timeout_seconds = 0.1

    def search(self, query: ResearchQuery) -> ResearchBatch:
        import time

        time.sleep(0.25)
        return super().search(query)


def test_queries_are_derived_from_plan_and_depth_is_bounded() -> None:
    agent = ResearchAgent()
    lithium = PlannerAgent().plan("Find hidden lithium dependencies behind Acme Electronics", depth="deep")
    semiconductors = PlannerAgent().plan("Find hidden semiconductor dependencies behind NVIDIA", depth="deep")
    lithium_queries = agent.generate_queries(lithium)
    semiconductor_queries = agent.generate_queries(semiconductors)

    assert lithium_queries
    assert {query.query for query in lithium_queries} != {query.query for query in semiconductor_queries}
    assert all("Acme Electronics" in query.query for query in lithium_queries)
    assert all("NVIDIA" in query.query for query in semiconductor_queries)
    assert max(query.depth for query in lithium_queries) <= lithium.depth
    assert len(agent.generate_queries(PlannerAgent().plan("Find lithium dependencies behind Acme Electronics", "standard"))) == 1
    assert len(agent.generate_queries(PlannerAgent().plan("Find lithium dependencies behind Acme Electronics", "maximum"))) <= 5


def test_start_research_requires_planned_status_and_authenticated_user(harness, monkeypatch: pytest.MonkeyPatch) -> None:
    client, factory = harness
    headers = _auth(client)
    investigation_id = _create_planned(client, headers)
    monkeypatch.setattr("app.api.v1.investigations.run_research_background", lambda _id: None)

    assert client.post(f"/api/investigations/{investigation_id}/research").status_code == 401
    started = client.post(f"/api/investigations/{investigation_id}/research", headers=headers)
    assert started.status_code == 202
    assert started.json()["status"] == "RESEARCHING"
    assert started.json()["research_mode"] == "local_demo"
    assert client.post(f"/api/investigations/{investigation_id}/research", headers=headers).status_code == 409
    assert client.get(f"/api/investigations/{investigation_id}/research", headers=headers).status_code == 200

    with factory() as db:
        investigation = db.get(Investigation, UUID(investigation_id))
        assert investigation is not None and investigation.status == "RESEARCHING"


def test_local_demo_completes_without_fabricating_evidence_or_graph_records(harness) -> None:
    client, factory = harness
    headers = _auth(client)
    investigation_id = _create_planned(client, headers)
    with factory() as db:
        investigation, provider = start_research(db, UUID(investigation_id))
        completed = execute_research(db, investigation.id, provider)
        assert completed.status == "COMPLETED"
        assert completed.research_mode == "local_demo"
        assert "external source discovery is not configured" in completed.research_progress["message"]
        assert db.scalar(select(Evidence.id).where(Evidence.investigation_id == investigation.id)) is None
        assert db.scalar(select(Entity.id).where(Entity.investigation_id == investigation.id)) is None
        assert db.scalar(select(Relationship.id).where(Relationship.investigation_id == investigation.id)) is None


def test_external_provider_persists_evidence_entities_and_evidence_backed_relationships(harness) -> None:
    client, factory = harness
    headers = _auth(client)
    investigation_id = _create_planned(client, headers)
    provider = DeterministicProvider()
    with factory() as db:
        investigation, _ = start_research(db, UUID(investigation_id))
        completed = execute_research(db, investigation.id, provider)
        assert completed.status == "COMPLETED"
        assert provider.queries
        evidence = db.scalars(select(Evidence).where(Evidence.investigation_id == investigation.id)).all()
        entities = db.scalars(select(Entity).where(Entity.investigation_id == investigation.id)).all()
        relationships = db.scalars(
            select(Relationship).where(Relationship.investigation_id == investigation.id)
        ).all()
        assert len(evidence) == len(provider.queries)
        assert {entity.name for entity in entities} >= {"Acme Electronics", "Supplier B"}
        assert relationships
        assert all(row.relationship_type == "SUPPLIES" for row in relationships)
        assert all(row.verification_status == "needs_review" for row in relationships)
        assert all(row.relationship_id is not None for row in evidence)
        assert evidence[0].metadata_json["provider"] == provider.name
        assert evidence[0].metadata_json["query"]
        assert completed.research_progress["relationships_found"] >= 1

    assert client.get(f"/api/investigations/{investigation_id}/evidence", headers=headers).json()["total"] > 0
    assert client.get(f"/api/investigations/{investigation_id}/entities", headers=headers).json()["total"] >= 2
    assert client.get(f"/api/investigations/{investigation_id}/relationships", headers=headers).json()["total"] > 0
    assert client.get("/api/graph", headers=headers).status_code == 200
    assert client.get(f"/api/investigations/{investigation_id}", headers=headers).json()["evidence_count"] > 0


def test_no_explicit_relation_phrase_creates_no_relationship(harness) -> None:
    client, factory = harness
    headers = _auth(client)
    investigation_id = _create_planned(client, headers)
    provider = DeterministicProvider("Supplier B and Acme Electronics appear in this source snippet.")
    with factory() as db:
        investigation, _ = start_research(db, UUID(investigation_id))
        execute_research(db, investigation.id, provider)
        assert db.scalar(select(Evidence.id).where(Evidence.investigation_id == investigation.id)) is not None
        assert db.scalar(select(Relationship.id).where(Relationship.investigation_id == investigation.id)) is None


def test_provider_failure_persists_failed_status_without_exposing_exception(harness) -> None:
    client, factory = harness
    headers = _auth(client)
    investigation_id = _create_planned(client, headers)
    with factory() as db:
        investigation, _ = start_research(db, UUID(investigation_id))
        with pytest.raises(ResearchExecutionError):
            execute_research(db, investigation.id, FailingProvider())
        failed = db.get(Investigation, investigation.id)
        assert failed is not None and failed.status == "FAILED"
        assert failed.error_message == "Research could not be completed."
        assert "private test failure detail" not in failed.error_message


def test_provider_timeout_persists_failed_status(harness) -> None:
    client, factory = harness
    investigation_id = _create_planned(client, _auth(client))
    with factory() as db:
        investigation, _ = start_research(db, UUID(investigation_id))
        with pytest.raises(ResearchExecutionError):
            execute_research(db, investigation.id, SlowProvider())
        failed = db.get(Investigation, investigation.id)
        assert failed is not None and failed.status == "FAILED"
        assert failed.error_message == "Research could not be completed."


def test_websocket_requires_authentication_and_sends_persisted_research_progress(harness, monkeypatch: pytest.MonkeyPatch) -> None:
    from starlette.websockets import WebSocketDisconnect

    client, _factory = harness
    headers = _auth(client)
    investigation_id = _create_planned(client, headers)
    monkeypatch.setattr("app.api.v1.investigations.run_research_background", lambda _id: None)
    assert client.post(f"/api/investigations/{investigation_id}/research", headers=headers).status_code == 202

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/investigations/{investigation_id}"):
            pass
    token = headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(
        f"/ws/investigations/{investigation_id}",
        subprotocols=["hdi", f"bearer.{token}"],
    ) as websocket:
        message = websocket.receive_json()
        assert message["type"] == "research_progress"
        assert message["status"] == "RESEARCHING"
        assert message["progress"]["total_steps"] > 0


def test_research_source_url_validation_blocks_private_destinations() -> None:
    assert validate_fetch_url("https://example.com/path") == "https://example.com/path"
    with pytest.raises(Exception):
        validate_fetch_url("http://127.0.0.1/private")
    with pytest.raises(Exception):
        UnconfiguredResearchProvider().fetch("https://example.com", ResearchQuery(
            query="example source search",
            purpose="test provider boundary",
            depth=1,
            step_id="step-1",
        ))
