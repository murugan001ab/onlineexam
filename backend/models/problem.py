from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import CreatedAtMixin, TimestampMixin


class Problem(Base, TimestampMixin):
    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("college_id", "slug", name="uq_problem_college_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text)
    constraints: Mapped[Optional[str]] = mapped_column(Text)
    starter_code: Mapped[Optional[str]] = mapped_column(Text)

    # easy | medium | hard
    difficulty: Mapped[Optional[str]] = mapped_column(String(30))

    time_limit_ms: Mapped[Optional[int]] = mapped_column(Integer)
    memory_limit_kb: Mapped[Optional[int]] = mapped_column(Integer)

    allowed_languages: Mapped[Optional[Any]] = mapped_column(JSONB)
    default_language: Mapped[Optional[str]] = mapped_column(String(20))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    problem_topics: Mapped[List["ProblemTopic"]] = relationship(back_populates="problem")
    test_cases: Mapped[List["TestCase"]] = relationship(back_populates="problem")
    submissions: Mapped[List["Submission"]] = relationship(back_populates="problem")
    unlocks: Mapped[List["ProblemUnlock"]] = relationship(back_populates="problem")
    training_assignments: Mapped[List["TrainingAssignment"]] = relationship(back_populates="problem")


class ProblemTopic(Base):
    __tablename__ = "problem_topics"

    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)

    problem: Mapped["Problem"] = relationship(back_populates="problem_topics")
    topic: Mapped["Topic"] = relationship()


class TestCase(Base, CreatedAtMixin):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)

    input: Mapped[Optional[str]] = mapped_column(Text)
    expected_output: Mapped[Optional[str]] = mapped_column(Text)

    is_hidden: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    order_index: Mapped[Optional[int]] = mapped_column(Integer)
    points: Mapped[Optional[int]] = mapped_column(Integer)

    problem: Mapped["Problem"] = relationship(back_populates="test_cases")


class Submission(Base, CreatedAtMixin):
    """Practice-mode submissions (unrelated to the one-shot prompt training flow)."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)

    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)

    language: Mapped[Optional[str]] = mapped_column(String(30))
    code: Mapped[Optional[str]] = mapped_column(Text)

    # queued | running | accepted | wrong_answer | runtime_error | compilation_error |
    # timeout | memory_limit
    status: Mapped[Optional[str]] = mapped_column(String(30))

    score: Mapped[Optional[int]] = mapped_column(Integer)
    max_score: Mapped[Optional[int]] = mapped_column(Integer)
    runtime_ms: Mapped[Optional[int]] = mapped_column(Integer)

    results: Mapped[Optional[Any]] = mapped_column(JSONB)

    problem: Mapped["Problem"] = relationship(back_populates="submissions")


class ProblemUnlock(Base):
    __tablename__ = "problem_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "problem_id", name="uq_problem_unlock"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)

    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    problem: Mapped["Problem"] = relationship(back_populates="unlocks")
