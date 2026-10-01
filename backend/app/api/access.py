from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Investigation
from app.models.user import User


def owned_investigation_ids(user: User):
    statement = select(Investigation.id)
    if not user.is_admin:
        statement = statement.where(
            or_(
                Investigation.owner_id == user.id,
                (Investigation.owner_id.is_(None) & Investigation.demo_mode.is_(True)),
            )
        )
    return statement


def get_accessible_investigation(db: Session, investigation_id: UUID, user: User) -> Investigation:
    statement = select(Investigation).where(Investigation.id == investigation_id)
    if not user.is_admin:
        statement = statement.where(
            or_(
                Investigation.owner_id == user.id,
                (Investigation.owner_id.is_(None) & Investigation.demo_mode.is_(True)),
            )
        )
    investigation = db.scalar(statement)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation
