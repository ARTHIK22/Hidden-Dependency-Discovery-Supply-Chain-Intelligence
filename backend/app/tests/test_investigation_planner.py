from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.planner import PlannerAgent
from app.agents.schemas import InvestigationPlan
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base, Entity, Investigation


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    sessions: list[Session] = []

    def override_db() -> Generator[Session, None, None]:
        with test_session() as db:
            sessions.append(db)
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "jwt_secret_key", "planner-test-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "database_url", None)
    app.state.planner_test_sessions = sessions
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.planner_test_sessions
        engine.dispose()


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Planner Tester",
            "email": f"{uuid4()}@example.test",
            "password": "planner-test-password",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create(client: TestClient, headers: dict[str, str], goal: str, depth: str = "deep"):
    return client.post(
        "/api/investigations",
        headers=headers,
        json={"goal": goal, "depth": depth},
    )


def test_planner_schema_is_strict_and_output_is_validated() -> None:
    plan = PlannerAgent().plan("Find hidden lithium dependencies behind Acme Electronics.")
    assert isinstance(plan, InvestigationPlan)
    assert plan.target == "Acme Electronics"
    assert plan.planner_mode == "local_demo"
    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate({**plan.model_dump(), "unexpected": True})


@pytest.mark.parametrize(
    ("goal", "target", "focus"),
    [
        ("Find hidden lithium dependencies behind Acme Electronics.", "Acme Electronics", "lithium"),
        ("Find hidden semiconductor dependencies behind NVIDIA", "NVIDIA", "semiconductor"),
        ("Investigate Apple's battery supply chain", "Apple", "battery"),
    ],
)
def test_planner_dynamically_extracts_target_and_objective(
    goal: str,
    target: str,
    focus: str,
) -> None:
    plan = PlannerAgent().plan(goal)
    assert plan.target == target
    assert focus in plan.objective.lower()
    assert plan.planner_mode == "local_demo"


def test_planner_preserves_ambiguous_target_and_respects_depth() -> None:
    planner = PlannerAgent()
    plan = planner.plan("Investigate battery supply chain", depth="standard")
    assert plan.target is None
    assert plan.target_clarification
    assert plan.depth == 1
    assert len(plan.steps) == 2
    assert planner.plan("Investigate battery supply chain", depth="maximum").depth == 3
    with pytest.raises(ValueError):
        planner.plan("Investigate battery supply chain", depth="invalid")


def test_create_persists_plan_and_retrieval_is_authenticated(client: TestClient) -> None:
    headers = _auth_headers(client)
    goal = "Find hidden semiconductor dependencies behind NVIDIA"
    response = _create(client, headers, goal, depth="maximum")

    assert response.status_code == 201
    created = response.json()
    investigation = created["investigation"]
    assert investigation["goal"] == goal
    assert investigation["status"] == "PLANNED"
    assert investigation["demo_mode"] is False
    assert investigation["planner_mode"] == "local_demo"
    assert investigation["objective"] == created["plan"]["objective"]
    assert created["plan"]["target"] == "NVIDIA"
    assert created["plan"]["depth"] == 3

    plan_response = client.get(
        f"/api/investigations/{investigation['id']}/plan", headers=headers
    )
    assert plan_response.status_code == 200
    assert plan_response.json() == created["plan"]
    assert client.get(f"/api/investigations/{investigation['id']}/plan").status_code == 401


def test_nvidia_and_ambiguous_investigations_keep_separate_targets_and_records(client: TestClient) -> None:
    headers = _auth_headers(client)
    acme_response = _create(client, headers, "Find hidden lithium dependencies behind Acme Electronics")
    nvidia_response = _create(client, headers, "Find hidden semiconductor dependencies behind NVIDIA")
    ambiguous_response = _create(client, headers, "Investigate battery supply chain")
    assert acme_response.status_code == nvidia_response.status_code == ambiguous_response.status_code == 201

    acme = acme_response.json()
    nvidia = nvidia_response.json()
    ambiguous = ambiguous_response.json()
    assert len({acme["investigation"]["id"], nvidia["investigation"]["id"], ambiguous["investigation"]["id"]}) == 3
    assert acme["plan"]["target"] == "Acme Electronics"
    assert nvidia["plan"]["target"] == "NVIDIA"
    assert ambiguous["plan"]["target"] is None
    assert ambiguous["plan"]["target_clarification"]

    sessions: list[Session] = app.state.planner_test_sessions
    db = sessions[-1]
    acme_id = acme["investigation"]["id"]
    nvidia_id = nvidia["investigation"]["id"]
    db.add(Entity(name="Acme-only fixture", entity_type="supplier", investigation_id=UUID(acme["investigation"]["id"])))
    db.commit()
    assert client.get(f"/api/investigations/{acme_id}/entities", headers=headers).json()["items"]
    assert client.get(f"/api/investigations/{nvidia_id}/entities", headers=headers).json()["items"] == []


def test_goal_and_depth_validation_reject_invalid_requests(client: TestClient) -> None:
    headers = _auth_headers(client)
    assert _create(client, headers, "").status_code == 422
    assert _create(client, headers, "A valid investigation goal", depth="extreme").status_code == 422
    assert client.post(
        "/api/investigations",
        headers={"Authorization": "Bearer invalid-token"},
        json={"goal": "Investigate Apple's battery supply chain"},
    ).status_code == 401


def test_creation_requires_authentication_and_keeps_existing_response_fields(client: TestClient) -> None:
    goal = "Investigate Apple's battery supply chain"
    assert _create(client, {}, goal).status_code == 401
    response = _create(client, _auth_headers(client), goal)
    assert response.status_code == 201
    payload = response.json()
    assert {"id", "name", "goal", "status", "progress", "scope", "depth"} <= set(
        payload["investigation"]
    )
    assert "plan" in payload


def test_status_is_planning_during_planner_execution(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = _auth_headers(client)
    observed: list[str] = []
    original_plan = PlannerAgent.plan

    def inspect_planning_status(
        planner: PlannerAgent,
        goal: str,
        depth: str = "deep",
        scope: dict[str, bool] | None = None,
    ) -> InvestigationPlan:
        sessions: list[Session] = app.state.planner_test_sessions
        rows = sessions[-1].scalars(select(Investigation)).all()
        observed.append(rows[-1].status)
        return original_plan(planner, goal, depth, scope)

    monkeypatch.setattr(PlannerAgent, "plan", inspect_planning_status)
    response = _create(client, headers, "Investigate Apple's battery supply chain")
    assert response.status_code == 201
    assert observed == ["PLANNING"]
    assert response.json()["investigation"]["status"] == "PLANNED"


def test_planner_failure_is_persisted_without_fake_plan(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _auth_headers(client)

    def fail_planning(*args: object, **kwargs: object) -> InvestigationPlan:
        raise ValueError("invalid planner output")

    monkeypatch.setattr(PlannerAgent, "plan", fail_planning)
    response = _create(client, headers, "Investigate Apple's battery supply chain")
    assert response.status_code == 500
    rows = app.state.planner_test_sessions[-1].scalars(select(Investigation)).all()
    assert rows[0].status == "FAILED"
    assert rows[0].plan is None
    assert rows[0].error_message == "Investigation planning failed."
