from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import CreatedAtMixin


class QuizAttempt(Base, CreatedAtMixin):
    """A student taking a class-test quiz (quiz_type='class'), assigned via
    QuizClassTarget. class_id records which class assignment the attempt was
    taken under (a quiz can in principle be targeted at more than one class)."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (UniqueConstraint("quiz_id", "student_id", name="uq_quiz_attempt_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # not_started | in_progress | submitted | expired | disqualified
    status: Mapped[Optional[str]] = mapped_column(String(30))

    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    max_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    quiz: Mapped["Quiz"] = relationship(back_populates="attempts")
    student: Mapped["Student"] = relationship()
    class_: Mapped["Class"] = relationship()
    answers: Mapped[List["QuizAnswer"]] = relationship(back_populates="attempt")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_quiz_answer_question"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("quiz_attempts.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)

    answer: Mapped[Optional[Any]] = mapped_column(JSONB)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    attempt: Mapped["QuizAttempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship()
