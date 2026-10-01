from sqlalchemy.orm import Session
from uuid import UUID

from app.agents.planner import PlannerAgent
from app.models import Investigation
from app.schemas.investigation import InvestigationCreate


class InvestigationPlanningError(Exception):
	pass


def create_planned_investigation(
	db: Session,
	payload: InvestigationCreate,
	owner_id: UUID | None = None,
) -> tuple[Investigation, dict[str, object]]:
	scope = {
		"geography": payload.scope_geography,
		"materials": payload.scope_materials,
		"manufacturers": payload.scope_manufacturers,
		"verification": payload.scope_verification,
	}
	name = (payload.name or payload.goal[:240]).strip()
	investigation = Investigation(
		name=name,
		goal=payload.goal.strip(),
		scope=scope,
		depth=payload.depth,
		status="QUEUED",
		progress=0,
		demo_mode=False,
		owner_id=owner_id,
	)
	db.add(investigation)
	db.commit()
	db.refresh(investigation)

	investigation.status = "PLANNING"
	db.commit()
	try:
		plan = PlannerAgent().plan(
			goal=investigation.goal,
			depth=investigation.depth,
			scope=scope,
		)
	except Exception as exc:
		db.rollback()
		failed = db.get(Investigation, investigation.id)
		if failed is not None:
			failed.status = "FAILED"
			failed.error_message = "Investigation planning failed."
			db.commit()
		raise InvestigationPlanningError from exc

	plan_data = plan.model_dump(mode="json")
	investigation.objective = plan.objective
	investigation.plan = plan_data
	investigation.planner_mode = plan.planner_mode
	investigation.status = "PLANNED"
	investigation.error_message = None
	db.commit()
	db.refresh(investigation)
	return investigation, plan_data
