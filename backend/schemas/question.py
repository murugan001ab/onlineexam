from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal["single_choice", "multiple_choice", "true_false"]
Difficulty = Literal["easy", "medium", "hard"]


class QuestionCreate(BaseModel):
    topic_id: Optional[int] = None
    text: str = Field(min_length=1)
    question_type: QuestionType = "single_choice"
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    marks: int = Field(default=1, ge=1)
    is_active: bool = True


class QuestionUpdate(BaseModel):
    topic_id: Optional[int] = None
    text: Optional[str] = Field(default=None, min_length=1)
    question_type: Optional[QuestionType] = None
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    marks: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class QuestionOut(BaseModel):
    """Staff view: includes correct_answer/explanation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    topic_id: Optional[int] = None
    text: str
    question_type: Optional[str] = None
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    marks: int
    is_active: bool
    created_by: int
    created_at: datetime


class QuestionPublicOut(BaseModel):
    """Student-facing view while attempting a quiz: no answer key."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: Optional[int] = None
    text: str
    question_type: Optional[str] = None
    options: Optional[Any] = None
    difficulty: Optional[str] = None
    marks: int
