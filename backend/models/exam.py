from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import CreatedAtMixin, TimestampMixin


class Exam(Base, TimestampMixin):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    exam_type_id: Mapped[int] = mapped_column(ForeignKey("exam_types.id"), nullable=False)

    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    # registration fee; null/0 means free
    fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    fee_currency: Mapped[str] = mapped_column(String(10), default="INR", server_default="INR")

    # draft | published | running | completed | cancelled
    status: Mapped[Optional[str]] = mapped_column(String(30))

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    exam_type: Mapped["ExamType"] = relationship(back_populates="exams")
    registrations: Mapped[List["ExamRegistration"]] = relationship(back_populates="exam")
    exam_quizzes: Mapped[List["ExamQuiz"]] = relationship(back_populates="exam")
    topic_weights: Mapped[List["ExamTopicWeight"]] = relationship(back_populates="exam")
    invitations: Mapped[List["ExamInvitation"]] = relationship(back_populates="exam")
    attempts: Mapped[List["ExamAttempt"]] = relationship(back_populates="exam")


class ExamQuiz(Base):
    __tablename__ = "exam_quizzes"
    __table_args__ = (UniqueConstraint("exam_id", "quiz_id", name="uq_exam_quiz"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)

    order_index: Mapped[Optional[int]] = mapped_column(Integer)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))

    exam: Mapped["Exam"] = relationship(back_populates="exam_quizzes")
    quiz: Mapped["Quiz"] = relationship(back_populates="exam_quizzes")


class ExamTopicWeight(Base):
    __tablename__ = "exam_topic_weights"
    __table_args__ = (UniqueConstraint("exam_id", "topic_id", name="uq_exam_topic_weight"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), nullable=False)

    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))

    exam: Mapped["Exam"] = relationship(back_populates="topic_weights")
    topic: Mapped["Topic"] = relationship(back_populates="exam_topic_weights")


class ExamInvitation(Base, CreatedAtMixin):
    """Created once registration closes. Creating this row is what provisions the `users` row
    (role=student) for the applicant — do not store credentials here directly, reference the
    user that was created so there is a single source of truth for login."""

    __tablename__ = "exam_invitations"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_invitation_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    registration_id: Mapped[Optional[int]] = mapped_column(ForeignKey("exam_registrations.id"))

    # the users row created at invite time (role=student); source of truth for login credentials
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    exam_token_hash: Mapped[Optional[str]] = mapped_column(String(255), unique=True)

    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # pending | sent | used | expired
    status: Mapped[Optional[str]] = mapped_column(String(30))

    exam: Mapped["Exam"] = relationship(back_populates="invitations")
    student: Mapped["Student"] = relationship()
    registration: Mapped[Optional["ExamRegistration"]] = relationship(back_populates="invitation")
    user: Mapped[Optional["User"]] = relationship()
