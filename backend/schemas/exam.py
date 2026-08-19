from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExamStatus = Literal["draft", "published", "running", "completed", "cancelled"]
SlotStatus = Literal["open", "closed", "cancelled"]


# --------------------------------------------------------------- exam types

class ExamTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None


class ExamTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None


class ExamTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None


# --------------------------------------------------------------------- exam

class ExamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    exam_type_id: int
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    fee: Optional[Decimal] = Field(default=None, ge=0)
    fee_currency: str = Field(default="INR", max_length=10)
    status: ExamStatus = "draft"
    proctoring_enabled: bool = True
    fullscreen_required: bool = True
    camera_required: bool = False
    max_tab_switch_warnings: int = Field(default=3, ge=0)

    @model_validator(mode="after")
    def _check_schedule(self) -> "ExamCreate":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class ExamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    exam_type_id: Optional[int] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    fee: Optional[Decimal] = Field(default=None, ge=0)
    fee_currency: Optional[str] = Field(default=None, max_length=10)
    status: Optional[ExamStatus] = None
    proctoring_enabled: Optional[bool] = None
    fullscreen_required: Optional[bool] = None
    camera_required: Optional[bool] = None
    max_tab_switch_warnings: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_schedule(self) -> "ExamUpdate":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    name: str
    description: Optional[str] = None
    exam_type_id: int
    exam_type_name: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    fee: Optional[Decimal] = None
    fee_currency: str = "INR"
    status: Optional[str] = None
    public_slug: Optional[str] = None
    public_url: Optional[str] = None
    proctoring_enabled: bool = True
    fullscreen_required: bool = True
    camera_required: bool = False
    max_tab_switch_warnings: int = 3
    registration_count: int = 0
    slot_count: int = 0
    created_by: int
    created_at: datetime


class ExamPublicOut(BaseModel):
    """Unauthenticated view served from /public/exams/{slug} — the page an
    applicant lands on from a WhatsApp/poster/QR link, before they sign up
    or log in. Deliberately excludes fee internals, created_by, etc."""

    name: str
    description: Optional[str] = None
    exam_type_name: Optional[str] = None
    college_name: str
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    fee: Optional[Decimal] = None
    fee_currency: str = "INR"
    status: Optional[str] = None
    open_slot_count: int = 0


# ---------------------------------------------------------------- exam quiz

class ExamQuizAssign(BaseModel):
    quiz_id: int
    order_index: Optional[int] = None
    weight: Optional[Decimal] = None


class ExamQuizUpdate(BaseModel):
    order_index: Optional[int] = None
    weight: Optional[Decimal] = None


class ExamQuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    quiz_name: str
    order_index: Optional[int] = None
    weight: Optional[Decimal] = None


# ------------------------------------------------------------- exam problem

class ExamProblemAssign(BaseModel):
    problem_id: int
    order_index: Optional[int] = None
    marks: Optional[Decimal] = None


class ExamProblemUpdate(BaseModel):
    order_index: Optional[int] = None
    marks: Optional[Decimal] = None


class ExamProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    problem_title: str
    order_index: Optional[int] = None
    marks: Optional[Decimal] = None


# --------------------------------------------------------- exam topic weight

class ExamTopicWeightCreate(BaseModel):
    topic_id: int
    question_count: int = Field(gt=0)
    weight: Optional[Decimal] = None


class ExamTopicWeightUpdate(BaseModel):
    question_count: Optional[int] = Field(default=None, gt=0)
    weight: Optional[Decimal] = None


class ExamTopicWeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    topic_name: str
    question_count: int
    weight: Optional[Decimal] = None


# ------------------------------------------------------------------ slots

class ExamSlotCreate(BaseModel):
    exam_id: int
    name: Optional[str] = Field(default=None, max_length=100)
    starts_at: datetime
    ends_at: datetime
    max_capacity: int = Field(gt=0)
    status: SlotStatus = "open"


class ExamSlotUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    max_capacity: Optional[int] = Field(default=None, gt=0)
    status: Optional[SlotStatus] = None


class ExamSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    exam_id: Optional[int] = None
    name: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    max_capacity: int
    status: Optional[str] = None
    booked_count: int = 0
    available: int = 0
