from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import CreatedAtMixin


class ExamAttempt(Base, CreatedAtMixin):
    __tablename__ = "exam_attempts"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_attempt_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # not_started | in_progress | submitted | expired | disqualified
    status: Mapped[Optional[str]] = mapped_column(String(30))

    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    max_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    exam: Mapped["Exam"] = relationship(back_populates="attempts")
    student: Mapped["Student"] = relationship()
    answers: Mapped[List["ExamAnswer"]] = relationship(back_populates="attempt")
    proctoring_events: Mapped[List["ProctoringEvent"]] = relationship(back_populates="attempt")
    proctoring_snapshots: Mapped[List["ProctoringSnapshot"]] = relationship(back_populates="attempt")


class ExamAnswer(Base):
    __tablename__ = "exam_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_exam_answer_question"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempts.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)

    answer: Mapped[Optional[Any]] = mapped_column(JSONB)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    attempt: Mapped["ExamAttempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="exam_answers")
