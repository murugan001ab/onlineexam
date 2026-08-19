from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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

    # Short, URL-safe, globally-unique slug used for the public share link
    # admins hand out (WhatsApp/poster/QR/portal): FRONTEND_URL/e/{public_slug}.
    # Unlike ExamInvitation.exam_token_hash (per-student, issued after
    # registration closes), this is a single link anyone can open to land on
    # the exam's public info + "apply" page.
    public_slug: Mapped[Optional[str]] = mapped_column(String(60), unique=True, index=True)

    # ---- proctoring / secure-exam configuration (see models/proctoring.py) ----
    proctoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    fullscreen_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    camera_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # tab_switch / window_blur / fullscreen_exit events allowed before the
    # attempt is auto-disqualified by routers/proctoring.py.
    max_tab_switch_warnings: Mapped[int] = mapped_column(Integer, default=3, server_default="3")

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    exam_type: Mapped["ExamType"] = relationship(back_populates="exams")
    registrations: Mapped[List["ExamRegistration"]] = relationship(back_populates="exam")
    slots: Mapped[List["ExamSlot"]] = relationship(back_populates="exam")
    exam_quizzes: Mapped[List["ExamQuiz"]] = relationship(back_populates="exam")
    exam_problems: Mapped[List["ExamProblem"]] = relationship(back_populates="exam")
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


class ExamProblem(Base):
    """Attaches a coding Problem (see models/problem.py) directly to an exam,
    alongside the MCQ quizzes in ExamQuiz — lets one entrance exam mix MCQ,
    true/false and code sections. Grading for the code section reads the
    student's best Submission for (problem_id, user) within the attempt
    window; see routers/attempt.py."""

    __tablename__ = "exam_problems"
    __table_args__ = (UniqueConstraint("exam_id", "problem_id", name="uq_exam_problem"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), nullable=False)

    order_index: Mapped[Optional[int]] = mapped_column(Integer)
    marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    exam: Mapped["Exam"] = relationship(back_populates="exam_problems")
    problem: Mapped["Problem"] = relationship()


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
