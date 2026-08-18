from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class Quiz(Base, TimestampMixin):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # entrance | class | placement
    quiz_type: Mapped[Optional[str]] = mapped_column(String(30))
    subject: Mapped[Optional[str]] = mapped_column(String(100))

    schedule_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    schedule_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # draft | published | archived
    status: Mapped[Optional[str]] = mapped_column(String(30))

    quiz_questions: Mapped[List["QuizQuestion"]] = relationship(back_populates="quiz")
    exam_quizzes: Mapped[List["ExamQuiz"]] = relationship(back_populates="quiz")
    class_targets: Mapped[List["QuizClassTarget"]] = relationship(back_populates="quiz")
    attempts: Mapped[List["QuizAttempt"]] = relationship(back_populates="quiz")


class QuizClassTarget(Base):
    """Direct staff -> class assignment for class-exam quizzes (no exam/registration wrapper needed)."""

    __tablename__ = "quiz_class_targets"
    __table_args__ = (UniqueConstraint("quiz_id", "class_id", name="uq_quiz_class_target"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)

    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    quiz: Mapped["Quiz"] = relationship(back_populates="class_targets")
    class_: Mapped["Class"] = relationship(back_populates="quiz_targets")
