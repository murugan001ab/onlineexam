from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

QuestionType = Literal["single_choice", "multiple_choice", "true_false"]
Difficulty = Literal["easy", "medium", "hard"]


def _validate_options_and_answer(question_type: Optional[str], options: Any, correct_answer: Any) -> None:
    """Shared shape/consistency check for options + correct_answer, used by
    both create (all fields required) and update (only re-checked when the
    request actually touches one of these three fields). Keeps bad data
    (answer key pointing at a nonexistent option, wrong shape for the type)
    out of the DB instead of only failing later when a student attempts the
    quiz."""
    if question_type == "true_false":
        if correct_answer not in (True, False, "True", "False", "true", "false"):
            raise ValueError("true_false questions need correct_answer to be True or False")
        return

    if question_type in ("single_choice", "multiple_choice"):
        if not isinstance(options, list) or len(options) < 2:
            raise ValueError(f"{question_type} questions need at least 2 options")
        if not all(isinstance(o, str) and o.strip() for o in options):
            raise ValueError("Every option must be non-empty text")
        if len(set(options)) != len(options):
            raise ValueError("Options must be unique")

        if question_type == "single_choice":
            if not isinstance(correct_answer, str) or correct_answer not in options:
                raise ValueError("correct_answer must be exactly one of the given options")
        else:  # multiple_choice
            if not isinstance(correct_answer, list) or not correct_answer:
                raise ValueError("multiple_choice questions need at least one correct_answer")
            if not all(a in options for a in correct_answer):
                raise ValueError("Every correct_answer entry must be one of the given options")
            if len(set(correct_answer)) != len(correct_answer):
                raise ValueError("correct_answer entries must be unique")


class QuestionCreate(BaseModel):
    topic_id: Optional[int] = None
    text: str = Field(min_length=1)
    question_type: QuestionType = "single_choice"
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    marks: int = Field(default=1, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def _check_answer_key(self) -> "QuestionCreate":
        _validate_options_and_answer(self.question_type, self.options, self.correct_answer)
        return self


class QuestionUpdate(BaseModel):
    topic_id: Optional[int] = None
    text: Optional[str] = Field(default=None, min_length=1)
    question_type: Optional[QuestionType] = None
    options: Optional[Any] = None
    correct_answer: Optional[Any] = None
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    marks: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def _check_answer_key(self) -> "QuestionUpdate":
        # Only re-validate when the request actually changes the answer-key
        # shape. Partial updates (e.g. only `marks`) are left alone here;
        # the router re-checks the merged result against the DB row before
        # committing (see routers/questions.py::_validate_answer_key).
        touched = self.model_fields_set & {"question_type", "options", "correct_answer"}
        if touched:
            _validate_options_and_answer(self.question_type, self.options, self.correct_answer)
        return self


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
    image_url: Optional[str] = None
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
    image_url: Optional[str] = None
    difficulty: Optional[str] = None
    marks: int
