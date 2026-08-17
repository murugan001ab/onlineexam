from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    created_by: int
    created_at: datetime


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
    name: Optional[str] = None
    starts_at: datetime
    ends_at: datetime
    max_capacity: int
    status: Optional[str] = None
    booked_count: int = 0
    available: int = 0
