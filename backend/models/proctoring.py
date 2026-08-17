from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"
    __table_args__ = (Index("ix_proctoring_events_attempt_occurred", "attempt_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempts.id"), nullable=False)

    # tab_switch | window_blur | fullscreen_exit | copy | paste | right_click | devtools |
    # face_missing | multiple_faces
    event_type: Mapped[Optional[str]] = mapped_column(String(50))
    metadata_: Mapped[Optional[Any]] = mapped_column("metadata", JSONB)

    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    attempt: Mapped["ExamAttempt"] = relationship(back_populates="proctoring_events")


class ProctoringSnapshot(Base):
    __tablename__ = "proctoring_snapshots"
    __table_args__ = (Index("ix_proctoring_snapshots_attempt_captured", "attempt_id", "captured_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("exam_attempts.id"), nullable=False)

    storage_key: Mapped[Optional[str]] = mapped_column(String(500))
    face_count: Mapped[Optional[int]] = mapped_column(Integer)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    attempt: Mapped["ExamAttempt"] = relationship(back_populates="proctoring_snapshots")
