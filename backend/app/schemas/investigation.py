from datetime import datetime

from pydantic import BaseModel, Field


class InvestigationCreate(BaseModel):
	goal: str = Field(..., min_length=20, max_length=5000)
	scope_manufacturers: bool = True
	scope_materials: bool = True
	scope_geography: bool = True
	scope_verification: bool = True
	depth: str = "deep"


class InvestigationResponse(BaseModel):
	id: str
	goal: str
	status: str
	depth: str
	created_at: datetime

	class Config:
		from_attributes = True
