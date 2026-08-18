from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AttemptStatus = Literal["not_started", "prompt_submitted", "debugging", "completed", "expired"]


# ------------------------------------------------------------- assignments

class TrainingAssignmentCreate(BaseModel):
    problem_id: int
    title: Optional[str] = Field(default=None, max_length=200)
    instructions: Optional[str] = None
    max_debug_submissions: Optional[int] = Field(default=None, gt=0)
    time_limit_minutes: Optional[int] = Field(default=None, gt=0)


class TrainingAssignmentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    instructions: Optional[str] = None
    max_debug_submissions: Optional[int] = Field(default=None, gt=0)
    time_limit_minutes: Optional[int] = Field(default=None, gt=0)


class TrainingAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    problem_id: int
    problem_title: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    max_debug_submissions: Optional[int] = None
    time_limit_minutes: Optional[int] = None
    created_by: int
    created_at: datetime


# ------------------------------------------------------------------ attempts

class TrainingAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    student_id: int
    status: AttemptStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    prompt: Optional[str] = None
    prompt_submitted_at: Optional[datetime] = None
    generated_code: Optional[str] = None
    generation_model: Optional[str] = None
    test_pass_rate: Optional[Decimal] = None
    debug_submission_count: int = 0
    max_debug_submissions: Optional[int] = None
    final_score: Optional[Decimal] = None


class PromptSubmit(BaseModel):
    prompt: str = Field(min_length=1)
    language: str = Field(default="python3")


# --------------------------------------------------------------- submissions

class TrainingSubmissionCreate(BaseModel):
    code: str = Field(min_length=1)
    language: str = Field(default="python3")


class TrainingSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    training_attempt_id: int
    code: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None
    max_score: Optional[int] = None
    runtime_ms: Optional[int] = None
    passed_test_cases: Optional[int] = None
    total_test_cases: Optional[int] = None
    results: Optional[Any] = None
    submitted_at: Optional[datetime] = None
