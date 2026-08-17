from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    registration_id: Mapped[int] = mapped_column(ForeignKey("exam_registrations.id"), nullable=False)

    # razorpay
    provider: Mapped[Optional[str]] = mapped_column(String(50))

    order_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    signature: Mapped[Optional[str]] = mapped_column(String(500))

    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(10), default="INR", server_default="INR")

    # created | pending | paid | failed | refunded
    status: Mapped[Optional[str]] = mapped_column(String(30))
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    raw_response: Mapped[Optional[Any]] = mapped_column(JSONB)

    registration: Mapped["ExamRegistration"] = relationship(back_populates="payments")
