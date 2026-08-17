from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import CreatedAtMixin, TimestampMixin


class TrainingAssignment(Base, TimestampMixin):
    __tablename__ = "training_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(200))
    instructions: Mapped[Optional[str]] = mapped_column(Text)

    max_debug_submissions: Mapped[Optional[int]] = mapped_column(Integer)
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    problem: Mapped["Problem"] = relationship(back_populates="training_assignments")
    attempts: Mapped[List["TrainingAttempt"]] = relationship(back_populates="assignment")


class TrainingAttempt(Base, CreatedAtMixin):
    """One-shot prompt -> LLM code -> student debug loop. `prompt_submitted_at` being set is the
    server-side lock: reject any further prompt submission once it is non-null, regardless of
    client state."""

    __tablename__ = "training_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("training_assignments.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # not_started | prompt_submitted | debugging | completed | expired
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started")

    prompt: Mapped[Optional[str]] = mapped_column(Text)
    prompt_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    generated_code: Mapped[Optional[str]] = mapped_column(Text)
    generation_model: Mapped[Optional[str]] = mapped_column(String(100))
    generation_input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    generation_output_tokens: Mapped[Optional[int]] = mapped_column(Integer)

    test_pass_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    debug_submission_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    final_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    assignment: Mapped["TrainingAssignment"] = relationship(back_populates="attempts")
    student: Mapped["Student"] = relationship()
    submissions: Mapped[List["TrainingSubmission"]] = relationship(back_populates="training_attempt")
    prompt_evaluations: Mapped[List["PromptEvaluation"]] = relationship(
        back_populates="training_attempt"
    )


class TrainingSubmission(Base):
    __tablename__ = "training_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    training_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("training_attempts.id"), nullable=False
    )

    code: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String(30))

    status: Mapped[Optional[str]] = mapped_column(String(30))

    score: Mapped[Optional[int]] = mapped_column(Integer)
    max_score: Mapped[Optional[int]] = mapped_column(Integer)
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer)

    passed_test_cases: Mapped[Optional[int]] = mapped_column(Integer)
    total_test_cases: Mapped[Optional[int]] = mapped_column(Integer)

    results: Mapped[Optional[Any]] = mapped_column(JSONB)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    training_attempt: Mapped["TrainingAttempt"] = relationship(back_populates="submissions")


class PromptEvaluation(Base):
    """Optional secondary score rating prompt-engineering quality itself (cheap model pass)."""

    __tablename__ = "prompt_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("training_attempts.id"), nullable=False
    )

    model: Mapped[Optional[str]] = mapped_column(String(100))
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    feedback: Mapped[Optional[str]] = mapped_column(Text)

    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    training_attempt: Mapped["TrainingAttempt"] = relationship(back_populates="prompt_evaluations")
