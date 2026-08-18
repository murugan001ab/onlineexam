import hashlib
from datetime import datetime, timezone
from typing import Optional

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from core.deps import CurrentUser, DbSession
from core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from models.auth import User
from models.exam import ExamInvitation

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class RedeemInvitationRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str] = None
    role: str
    college_id: Optional[int] = None
    is_active: bool


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession):
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest):
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    return AccessTokenResponse(access_token=create_access_token(int(claims["sub"])))


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser):
    return MeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        college_id=user.college_id,
        is_active=user.is_active,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordRequest, db: DbSession, user: CurrentUser):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


@router.post("/redeem-invitation", response_model=TokenResponse)
def redeem_invitation(payload: RedeemInvitationRequest, db: DbSession):
    """Pre-auth: the invitation token itself is the credential here, same as
    a password-reset link. Sets the student's real password, marks the
    invitation used, and logs them straight in (access + refresh tokens) so
    the frontend doesn't need a separate login round-trip right after."""
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = db.execute(
        select(ExamInvitation).where(ExamInvitation.exam_token_hash == token_hash)
    ).scalar_one_or_none()

    if invitation is None or invitation.status == "used":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or already-used invitation token")
    if invitation.expires_at is not None and invitation.expires_at <= datetime.now(timezone.utc):
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invitation has expired — ask your college to resend it")
    if invitation.user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invitation has no login attached")

    user = db.get(User, invitation.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The account for this invitation is not available")

    user.password_hash = hash_password(payload.new_password)
    user.last_login_at = datetime.now(timezone.utc)
    invitation.status = "used"
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
