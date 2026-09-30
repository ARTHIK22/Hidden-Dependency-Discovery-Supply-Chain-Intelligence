from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import get_user, list_users

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me", response_model=UserRead, summary="Update the current user's profile")
def update_profile(payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.full_name = payload.full_name.strip()
    db.add(AuditLog(user_id=user.id, action="profile_updated", resource_type="user", resource_id=str(user.id), metadata_json={}))
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead], summary="List users (admin only)")
def users(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return list_users(db, limit, offset)


@router.get("/{user_id}", response_model=UserRead, summary="Get the current user or an admin-selected user")
def user_by_id(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(403, "Users may only view their own profile")
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user
