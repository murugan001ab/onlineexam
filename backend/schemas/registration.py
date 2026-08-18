from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RegistrationStatus = Literal["pending_payment", "payment_failed", "confirmed", "cancelled", "completed"]
InvitationStatus = Literal["pending", "sent", "used", "expired"]


# ------------------------------------------------------------------- holds

class SlotHoldCreate(BaseModel):
    slot_id: int


class SlotHoldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    student_id: int
    expires_at: datetime
    status: Optional[str] = None


# ------------------------------------------------------------ registrations

class RegistrationCreate(BaseModel):
    exam_id: int
    hold_id: int


class ExamRegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    student_id: int
    exam_id: int
    exam_name: Optional[str] = None
    slot_id: Optional[int] = None
    registration_number: Optional[str] = None
    status: RegistrationStatus
    fee: Optional[Decimal] = None
    fee_currency: str = "INR"
    registered_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None


# ------------------------------------------------------------------ payment

class PaymentOrderCreate(BaseModel):
    registration_id: int


class PaymentOrderOut(BaseModel):
    payment_id: int
    order_id: str
    amount: Decimal
    currency: str
    key_id: Optional[str] = None
    """Razorpay public key_id for the checkout widget; null when running in mock mode."""


class PaymentVerify(BaseModel):
    registration_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_id: int
    provider: Optional[str] = None
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "INR"
    status: Optional[str] = None
    paid_at: Optional[datetime] = None


# --------------------------------------------------------------- invitation

class InvitationGenerate(BaseModel):
    registration_ids: Optional[list[int]] = None
    """If omitted, invitations are generated for every confirmed registration on the exam
    that doesn't already have one."""
    expires_in_hours: int = Field(default=72, gt=0)


class ExamInvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    student_id: int
    registration_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: Optional[str] = None
    created_at: datetime


class ExamInvitationWithToken(ExamInvitationOut):
    """Returned only right after generate/resend — the plaintext token is
    never stored (only its hash is), so this is the one chance to hand it
    to the caller for delivery (email/SMS/manual)."""

    token: str
