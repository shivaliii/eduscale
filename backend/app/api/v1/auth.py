"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.services.auth_service import (
    authenticate_user, create_access_token, create_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut(
            id=user.id, email=user.email, full_name=user.full_name,
            role=user.role.value, avatar_url=user.avatar_url,
        ),
    )


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role.value, avatar_url=user.avatar_url,
    )


@router.post("/logout")
def logout():
    # JWT is stateless; frontend should discard the token
    return {"message": "Logged out successfully"}
