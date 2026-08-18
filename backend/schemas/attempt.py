from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AttemptStatus = Literal["not_started", "in_progress", "submitted", "expired", "disqualified"]


class ExamAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    exam_name: Optional[str] = None
    student_id: int
    status: AttemptStatus
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    score: Optional[Decimal] = None
    max_score: Optional[Decimal] = None


class AnswerSubmit(BaseModel):
    question_id: int
    answer: Any


class ExamAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer: Optional[Any] = None
    is_correct: Optional[bool] = None
    marks: Optional[Decimal] = None
    answered_at: Optional[datetime] = None


class ExamAnswerReview(ExamAnswerOut):
    """Staff-only grading view: includes the question text and correct answer."""

    question_text: str
    correct_answer: Optional[Any] = None
