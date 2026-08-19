from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Difficulty = Literal["easy", "medium", "hard"]

SubmissionStatusLiteral = Literal[
    "queued",
    "running",
    "accepted",
    "wrong_answer",
    "runtime_error",
    "compilation_error",
    "timeout",
    "memory_limit",
]


class TopicBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ---------------------------------------------------------------- test cases

class TestCaseCreate(BaseModel):
    input: Optional[str] = None
    expected_output: Optional[str] = None
    is_hidden: bool = True
    order_index: Optional[int] = None
    points: Optional[int] = None


class TestCaseUpdate(BaseModel):
    input: Optional[str] = None
    expected_output: Optional[str] = None
    is_hidden: Optional[bool] = None
    order_index: Optional[int] = None
    points: Optional[int] = None


class TestCaseOut(BaseModel):
    """Public view. expected_output is stripped for hidden cases unless
    reveal_hidden=True (staff, or grading internals) via from_test_case()."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    input: Optional[str] = None
    expected_output: Optional[str] = None
    is_hidden: bool
    order_index: Optional[int] = None
    points: Optional[int] = None

    @classmethod
    def from_test_case(cls, tc, *, reveal_hidden: bool = False) -> "TestCaseOut":
        return cls(
            id=tc.id,
            input=tc.input,
            expected_output=tc.expected_output if (reveal_hidden or not tc.is_hidden) else None,
            is_hidden=tc.is_hidden,
            order_index=tc.order_index,
            points=tc.points,
        )


# -------------------------------------------------------------------- problem

class ProblemBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=220)
    description: Optional[str] = None
    constraints: Optional[str] = None
    starter_code: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    time_limit_ms: Optional[int] = Field(default=None, gt=0)
    memory_limit_kb: Optional[int] = Field(default=None, gt=0)
    allowed_languages: Optional[list[str]] = None
    default_language: Optional[str] = None
    is_active: bool = True


class ProblemCreate(ProblemBase):
    topic_ids: list[int] = Field(default_factory=list)


class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=220)
    description: Optional[str] = None
    constraints: Optional[str] = None
    starter_code: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    time_limit_ms: Optional[int] = Field(default=None, gt=0)
    memory_limit_kb: Optional[int] = Field(default=None, gt=0)
    allowed_languages: Optional[list[str]] = None
    default_language: Optional[str] = None
    is_active: Optional[bool] = None
    topic_ids: Optional[list[int]] = None


class ProblemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    title: str
    slug: str
    difficulty: Optional[str] = None
    is_active: bool


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    college_id: int
    title: str
    slug: str
    description: Optional[str] = None
    constraints: Optional[str] = None
    starter_code: Optional[str] = None
    difficulty: Optional[str] = None
    time_limit_ms: Optional[int] = None
    memory_limit_kb: Optional[int] = None
    allowed_languages: Optional[list[str]] = None
    default_language: Optional[str] = None
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    topics: list[TopicBrief] = Field(default_factory=list)
    test_cases: list[TestCaseOut] = Field(default_factory=list)


# ----------------------------------------------------------------- submission

class SubmissionCreate(BaseModel):
    problem_id: int
    language: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1)


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    problem_id: int
    user_id: int
    language: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None
    max_score: Optional[int] = None
    runtime_ms: Optional[int] = None
    results: Optional[Any] = None
    created_at: datetime


class SubmissionAdminOut(SubmissionOut):
    """Staff/admin review view — adds student and problem context, plus the
    submitted code, so a submissions list doesn't require N follow-up
    lookups."""

    code: Optional[str] = None
    student_id: int
    student_username: Optional[str] = None
    problem_title: Optional[str] = None
    passed_count: Optional[int] = None
    total_count: Optional[int] = None

    @classmethod
    def from_submission(cls, sub, *, student_username: Optional[str], problem_title: Optional[str]) -> "SubmissionAdminOut":
        results = sub.results if isinstance(sub.results, list) else None
        passed_count = sum(1 for r in results if r.get("passed")) if results else None
        total_count = len(results) if results else None
        return cls(
            id=sub.id,
            uuid=sub.uuid,
            problem_id=sub.problem_id,
            user_id=sub.user_id,
            language=sub.language,
            code=sub.code,
            status=sub.status,
            score=sub.score,
            max_score=sub.max_score,
            runtime_ms=sub.runtime_ms,
            results=sub.results,
            created_at=sub.created_at,
            student_id=sub.user_id,
            student_username=student_username,
            problem_title=problem_title,
            passed_count=passed_count,
            total_count=total_count,
        )


# -------------------------------------------------------------------- unlock

class ProblemUnlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    problem_id: int
    user_id: int
    unlocked_at: Optional[datetime] = None
