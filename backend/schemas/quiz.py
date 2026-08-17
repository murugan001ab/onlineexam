from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

QuizType = Literal["entrance", "class", "placement"]
QuizStatus = Literal["draft", "published", "archived"]


class QuizCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    quiz_type: QuizType
    subject: Optional[str] = Field(default=None, max_length=100)
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    status: QuizStatus = "draft"


class QuizUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    subject: Optional[str] = Field(default=None, max_length=100)
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    status: Optional[QuizStatus] = None


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    name: str
    description: Optional[str] = None
    quiz_type: Optional[str] = None
    subject: Optional[str] = None
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    created_by: int
    created_at: datetime
    question_count: int = 0


# ------------------------------------------------------------- quiz questions

class QuizQuestionAdd(BaseModel):
    question_id: int
    order_index: Optional[int] = None
    marks: Optional[int] = Field(default=None, ge=1)


class QuizQuestionReorder(BaseModel):
    order_index: Optional[int] = None
    marks: Optional[int] = Field(default=None, ge=1)


class QuizQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    order_index: Optional[int] = None
    marks: Optional[int] = None
    text: str
    question_type: Optional[str] = None
    difficulty: Optional[str] = None


# ------------------------------------------------------------ class targets

class QuizClassTargetAssign(BaseModel):
    class_id: int


class QuizClassTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    class_id: int
    class_name: str
    assigned_by: int
    assigned_at: Optional[datetime] = None
