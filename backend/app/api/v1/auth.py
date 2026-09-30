from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Register an analyst account")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_user(db, payload.email, payload.password, payload.full_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.add(AuditLog(user_id=user.id, action="register", resource_type="user", resource_id=str(user.id), metadata_json={}))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=TokenResponse, summary="Authenticate and issue a JWT")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    db.add(AuditLog(user_id=user.id, action="login", resource_type="user", resource_id=str(user.id), metadata_json={}))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserRead, summary="Get the authenticated user")
def me(user: User = Depends(get_current_user)):
    return user
