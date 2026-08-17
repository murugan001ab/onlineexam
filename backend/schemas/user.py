from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ManagedRole = Literal["admin", "staff"]


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    dob: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    dob: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    phone: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: str = Field(min_length=8, max_length=128)
    role: ManagedRole
    # Required when the caller is super_admin. Ignored (forced to the
    # caller's own college) when the caller is admin creating staff.
    college_id: Optional[int] = None
    profile: ProfileIn


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    is_active: Optional[bool] = None
    # Reassigning college is a super_admin-only action, enforced in the router.
    college_id: Optional[int] = None
    profile: Optional[ProfileUpdate] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str] = None
    role: str
    college_id: Optional[int] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    profile: Optional[ProfileOut] = None
