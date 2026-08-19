from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.mixins import CreatedAtMixin


class OtpVerification(Base, CreatedAtMixin):
    """Short-lived one-time codes used to verify an email address or phone
    number before self-service applicant signup completes.

    Each "send" inserts a fresh row rather than reusing an old one, so a
    contact can have several rows over time — callers should always query
    for the most recent unexpired, unverified row for a given
    (contact_type, contact, purpose).
    """

    __tablename__ = "otp_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # "email" | "phone"
    contact_type: Mapped[str] = mapped_column(String(10), nullable=False)
    contact: Mapped[str] = mapped_column(String(255), nullable=False)

    # What this code is for. Only "signup" today, but keeping this column
    # means "password_reset" etc. can reuse the same table later.
    purpose: Mapped[str] = mapped_column(String(30), nullable=False, default="signup")

    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
