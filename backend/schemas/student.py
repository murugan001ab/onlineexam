from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.user import ProfileIn, ProfileOut, ProfileUpdate

StudentStage = Literal["applicant", "enrolled"]


class StudentCreate(BaseModel):
    email: Optional[str] = None
    register_number: Optional[str] = Field(default=None, max_length=100)
    application_number: Optional[str] = Field(default=None, max_length=100)
    stage: StudentStage = "applicant"
    tenth_mark: Optional[Decimal] = Field(default=None, ge=0, le=100)
    twelfth_mark: Optional[Decimal] = Field(default=None, ge=0, le=100)
    diploma_mark: Optional[Decimal] = Field(default=None, ge=0, le=100)
    is_diploma: bool = False
    profile: ProfileIn


class StudentUpdate(BaseModel):
    email: Optional[str] = None
    register_number: Optional[str] = Field(default=None, max_length=100)
    application_number: Optional[str] = Field(default=None, max_length=100)
    stage: Optional[StudentStage] = None
    tenth_mark: Optional[Decimal] = Field(default=None, ge=0, le=100)
    twelfth_mark: Optional[Decimal] = Field(default=None, ge=0, le=100)
    diploma_mark: Optional[Decimal] = Field(default=None, ge=0, le=100)
    is_diploma: Optional[bool] = None
    admitted_at: Optional[datetime] = None
    profile: Optional[ProfileUpdate] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    email: Optional[str] = None
    register_number: Optional[str] = None
    application_number: Optional[str] = None
    stage: str
    tenth_mark: Optional[Decimal] = None
    twelfth_mark: Optional[Decimal] = None
    diploma_mark: Optional[Decimal] = None
    is_diploma: bool
    admitted_at: Optional[datetime] = None
    has_login: bool
    profile: Optional[ProfileOut] = None


class StudentClassAssign(BaseModel):
    class_id: int
    academic_year: Optional[str] = Field(default=None, max_length=20)


class StudentClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    class_name: str
    academic_year: Optional[str] = None
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None


class StudentLoginCreate(BaseModel):
    # If omitted, a username is auto-generated from register/application number or name.
    username: Optional[str] = Field(default=None, min_length=3, max_length=100)


class StudentLoginUpdate(BaseModel):
    is_active: Optional[bool] = None
    # If true, a new random password is generated and returned once in the response.
    reset_password: bool = False


class StudentLoginOut(BaseModel):
    user_id: int
    username: str
    is_active: bool
    # Only populated right after creation or a password reset — never re-shown after.
    temporary_password: Optional[str] = None
