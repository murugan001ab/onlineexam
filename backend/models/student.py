from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("college_id", "application_number", name="uq_student_application_number"),
        UniqueConstraint("college_id", "register_number", name="uq_student_register_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    # null until an invite creates the login (applicant stage)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), unique=True)
    profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("profiles.id"))
    email: Mapped[Optional[str]] = mapped_column(String(255))

    register_number: Mapped[Optional[str]] = mapped_column(String(100))
    application_number: Mapped[Optional[str]] = mapped_column(String(100))

    # applicant | enrolled
    stage: Mapped[str] = mapped_column(String(30), nullable=False, default="applicant")

    tenth_mark: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    twelfth_mark: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    diploma_mark: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    is_diploma: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    admitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    college: Mapped["College"] = relationship(back_populates="students")
    user: Mapped[Optional["User"]] = relationship(back_populates="student")
    profile: Mapped[Optional["Profile"]] = relationship(back_populates="student")
    student_classes: Mapped[List["StudentClass"]] = relationship(back_populates="student")


class StudentClass(Base):
    __tablename__ = "student_classes"
    __table_args__ = (UniqueConstraint("student_id", "class_id", name="uq_student_class"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)

    academic_year: Mapped[Optional[str]] = mapped_column(String(20))
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    student: Mapped["Student"] = relationship(back_populates="student_classes")
    class_: Mapped["Class"] = relationship(back_populates="student_classes")
