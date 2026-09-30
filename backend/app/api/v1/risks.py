from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.risk_service import analyze_supplier_risk

router = APIRouter(prefix="/risks", tags=["Risks"])


@router.get("/analysis", summary="Analyze recorded supplier concentration and single-source risks")
def get_risk_analysis(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {"risks": analyze_supplier_risk(db), "basis": "recorded relationship data", "external_risk_feeds_used": False}
