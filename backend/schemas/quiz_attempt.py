from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

AttemptStatus = Literal["not_started", "in_progress", "submitted", "expired", "disqualified"]


class QuizAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    quiz_name: Optional[str] = None
    class_id: int
    student_id: int
    status: AttemptStatus
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    score: Optional[Decimal] = None
    max_score: Optional[Decimal] = None


class QuizAnswerSubmit(BaseModel):
    question_id: int
    answer: Any


class QuizAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer: Optional[Any] = None
    is_correct: Optional[bool] = None
    marks: Optional[Decimal] = None
    answered_at: Optional[datetime] = None


class QuizAnswerReview(QuizAnswerOut):
    """Staff-only grading view: includes the question text and correct answer."""

    question_text: str
    correct_answer: Optional[Any] = None


class QuizAvailableOut(BaseModel):
    """A class quiz visible to a student through one of their active class
    enrollments, plus their attempt (if any) so the client knows whether to
    show 'start' or 'resume'."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    class_id: int
    class_name: str
    attempt_id: Optional[int] = None
    attempt_status: Optional[AttemptStatus] = None
