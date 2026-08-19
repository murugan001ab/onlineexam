from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class StudentDocument(Base, TimestampMixin):
    """Applicant-uploaded proof documents (10th/12th/diploma marksheet, age
    proof, photo) collected on the registration form. Staff review each one
    independently so a rejected age-proof doesn't block re-checking an
    already-approved 12th marksheet.
    """

    __tablename__ = "student_documents"
    __table_args__ = (
        UniqueConstraint("student_id", "doc_type", name="uq_student_document_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)

    # tenth_marksheet | twelfth_marksheet | diploma_marksheet | age_proof | photo
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Where a document states a place/board (e.g. "10th std stated at ...")
    # so admin can cross-check against the college's home-state rules.
    issued_place: Mapped[Optional[str]] = mapped_column(String(150))
    issuing_board: Mapped[Optional[str]] = mapped_column(String(150))

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(100))

    # pending | verified | rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    student: Mapped["Student"] = relationship()
