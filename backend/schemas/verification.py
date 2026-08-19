from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

ContactType = Literal["email", "phone"]


class SendOtpRequest(BaseModel):
    contact_type: ContactType
    # Validated as an email only when contact_type == "email"; kept as a
    # plain string here so phone numbers (which aren't emails) pass through
    # the same endpoint. The router re-validates the format itself.
    contact: str = Field(min_length=3, max_length=255)


class SendOtpResponse(BaseModel):
    contact_type: ContactType
    contact: str
    expires_in_seconds: int
    # Only present when SMTP/SMS isn't configured, so the developer can
    # still test the flow locally without real delivery.
    debug_code: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    contact_type: ContactType
    contact: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=4, max_length=8)


class VerifyOtpResponse(BaseModel):
    contact_type: ContactType
    contact: str
    verified: bool


class PublicCollegeOut(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None


class ApplicantSignupRequest(BaseModel):
    college_id: int
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    dob: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=30)
    tenth_mark: Optional[float] = Field(default=None, ge=0, le=100)
    twelfth_mark: Optional[float] = Field(default=None, ge=0, le=100)


class ApplicantSignupResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    username: str
    student_id: int
