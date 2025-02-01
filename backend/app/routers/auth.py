from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, serialize_auth_user, verify_password
from app.database import get_db
from app.models import User
from app.schemas import AuthResponse, AuthUserResponse, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login_id == payload.login_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=create_access_token(subject=user.id, role=user.role),
        user=AuthUserResponse(**serialize_auth_user(user)),
    )


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: User = Depends(get_current_user)):
    return AuthUserResponse(**serialize_auth_user(current_user))
