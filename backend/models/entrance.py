from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import CreatedAtMixin, TimestampMixin


class ExamSlot(Base, TimestampMixin):
    """Capacity-bounded FCFS booking slot. Booking must wrap capacity check + hold insert in a
    SELECT ... FOR UPDATE on this row (or an equivalent Redis atomic counter) to avoid overselling
    under concurrent requests."""

    __tablename__ = "exam_slots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    name: Mapped[Optional[str]] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    # open | closed | cancelled
    status: Mapped[Optional[str]] = mapped_column(String(30))

    registrations: Mapped[List["ExamRegistration"]] = relationship(back_populates="slot")
    holds: Mapped[List["SlotHold"]] = relationship(back_populates="slot")


class ExamRegistration(Base):
    __tablename__ = "exam_registrations"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_registration_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    slot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("exam_slots.id"))

    registration_number: Mapped[Optional[str]] = mapped_column(String(100))

    # pending_payment | payment_failed | confirmed | cancelled | completed
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_payment")

    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    student: Mapped["Student"] = relationship()
    exam: Mapped["Exam"] = relationship(back_populates="registrations")
    slot: Mapped[Optional["ExamSlot"]] = relationship(back_populates="registrations")
    payments: Mapped[List["Payment"]] = relationship(back_populates="registration")
    invitation: Mapped[Optional["ExamInvitation"]] = relationship(
        back_populates="registration", uselist=False
    )


class SlotHold(Base, CreatedAtMixin):
    """Temporary reservation (e.g. 10 min TTL) created when checkout starts; released on expiry,
    converted to a confirmed registration on successful payment."""

    __tablename__ = "slot_holds"
    __table_args__ = (UniqueConstraint("slot_id", "student_id", name="uq_slot_hold_student"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("exam_slots.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    registration_id: Mapped[Optional[int]] = mapped_column(ForeignKey("exam_registrations.id"))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # held | expired | converted | released
    status: Mapped[Optional[str]] = mapped_column(String(30))

    slot: Mapped["ExamSlot"] = relationship(back_populates="holds")
    student: Mapped["Student"] = relationship()
    registration: Mapped[Optional["ExamRegistration"]] = relationship()
