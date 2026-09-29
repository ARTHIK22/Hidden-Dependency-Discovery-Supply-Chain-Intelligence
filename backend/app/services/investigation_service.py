from uuid import uuid4

from app.schemas.investigation import InvestigationCreate


class InvestigationService:
	@staticmethod
	def create(payload: InvestigationCreate) -> dict:
		return {
			"id": str(uuid4()),
			"goal": payload.goal,
			"status": "queued",
			"depth": payload.depth,
			"scope": {
				"manufacturers": payload.scope_manufacturers,
				"materials": payload.scope_materials,
				"geography": payload.scope_geography,
				"verification": payload.scope_verification,
			},
		}
