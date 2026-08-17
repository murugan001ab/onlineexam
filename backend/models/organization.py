from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("college_id", "name", name="uq_department_college_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))

    college: Mapped["College"] = relationship(back_populates="departments")
    classes: Mapped[List["Class"]] = relationship(back_populates="department")
    staff_departments: Mapped[List["StaffDepartment"]] = relationship(back_populates="department")


class Class(Base, TimestampMixin):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("department_id", "name", "section", name="uq_class_department_name_section"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20))
    section: Mapped[Optional[str]] = mapped_column(String(20))

    college: Mapped["College"] = relationship(back_populates="classes")
    department: Mapped["Department"] = relationship(back_populates="classes")
    staff_classes: Mapped[List["StaffClass"]] = relationship(back_populates="class_")
    student_classes: Mapped[List["StudentClass"]] = relationship(back_populates="class_")
    quiz_targets: Mapped[List["QuizClassTarget"]] = relationship(back_populates="class_")


class StaffDepartment(Base):
    __tablename__ = "staff_departments"
    __table_args__ = (UniqueConstraint("user_id", "department_id", name="uq_staff_department"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    user: Mapped["User"] = relationship()
    department: Mapped["Department"] = relationship(back_populates="staff_departments")


class StaffClass(Base):
    __tablename__ = "staff_classes"
    __table_args__ = (UniqueConstraint("staff_id", "class_id", name="uq_staff_class"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)

    is_incharge: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    staff: Mapped["User"] = relationship()
    class_: Mapped["Class"] = relationship(back_populates="staff_classes")
