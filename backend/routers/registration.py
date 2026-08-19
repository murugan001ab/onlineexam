import hashlib
import secrets
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, CurrentUser, DbSession, require_roles
from core.security import hash_password
from core.settings import Settings
from models.auth import Role, User
from models.entrance import ExamRegistration, ExamSlot, SlotHold
from models.exam import Exam, ExamInvitation
from models.payment import Payment
from models.student import Student
from schemas.exam import ExamOut, ExamSlotOut
from schemas.registration import (
    ExamInvitationOut,
    ExamInvitationWithToken,
    ExamRegistrationOut,
    InvitationGenerate,
    PaymentOrderCreate,
    PaymentOrderOut,
    PaymentOut,
    PaymentVerify,
    RegistrationCreate,
    SlotHoldCreate,
    SlotHoldOut,
)
from utils.payments import create_order, is_live, verify_signature
from utils.email import send_exam_invitation, send_registration_confirmation

student_router = APIRouter(prefix="/entrance", tags=["entrance-exam-registration"])
admin_router = APIRouter(prefix="/admin", tags=["entrance-exam-registration"])

_ACTIVE_REGISTRATION_STATUSES = ("pending_payment", "confirmed", "completed")
RequireStudent = Depends(require_roles("student"))


def _get_student_or_404(db: DbSession, user: User) -> Student:
    student = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return student


def _slot_booked_count(db: DbSession, slot_id: int) -> int:
    confirmed = db.execute(
        select(func.count(ExamRegistration.id)).where(
            ExamRegistration.slot_id == slot_id,
            ExamRegistration.status.in_(_ACTIVE_REGISTRATION_STATUSES),
        )
    ).scalar_one()
    held = db.execute(
        select(func.count(SlotHold.id)).where(
            SlotHold.slot_id == slot_id,
            SlotHold.status == "held",
            SlotHold.expires_at > datetime.now(timezone.utc),
        )
    ).scalar_one()
    return confirmed + held


def _serialize_registration(reg: ExamRegistration) -> ExamRegistrationOut:
    return ExamRegistrationOut(
        id=reg.id,
        college_id=reg.college_id,
        student_id=reg.student_id,
        exam_id=reg.exam_id,
        exam_name=reg.exam.name if reg.exam else None,
        slot_id=reg.slot_id,
        registration_number=reg.registration_number,
        status=reg.status,
        fee=reg.exam.fee if reg.exam else None,
        fee_currency=reg.exam.fee_currency if reg.exam else "INR",
        registered_at=reg.registered_at,
        confirmed_at=reg.confirmed_at,
    )


def _serialize_slot(db: DbSession, slot: ExamSlot) -> ExamSlotOut:
    booked = _slot_booked_count(db, slot.id)
    return ExamSlotOut(
        id=slot.id,
        college_id=slot.college_id,
        exam_id=slot.exam_id,
        name=slot.name,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        max_capacity=slot.max_capacity,
        status=slot.status,
        booked_count=booked,
        available=max(slot.max_capacity - booked, 0),
    )


# ==================================================================
# Student-facing: browse exams/slots, holds, registration, payment
# ==================================================================

@student_router.get("/exams", response_model=list[ExamOut])
def list_open_exams(db: DbSession, user: User = RequireStudent):
    """Published exams open for application, scoped to the caller's college.
    Unlike /admin/exams (staff-only), this is reachable by the 'student' role."""
    student = _get_student_or_404(db, user)
    exams = db.execute(
        select(Exam)
        .where(Exam.college_id == student.college_id, Exam.status == "published")
        .options(selectinload(Exam.exam_type))
        .order_by(Exam.starts_at)
    ).scalars().all()
    return [
        ExamOut(
            id=e.id, college_id=e.college_id, name=e.name, description=e.description,
            exam_type_id=e.exam_type_id, exam_type_name=e.exam_type.name if e.exam_type else None,
            starts_at=e.starts_at, ends_at=e.ends_at, duration_minutes=e.duration_minutes,
            fee=e.fee, fee_currency=e.fee_currency, status=e.status, created_by=e.created_by,
            created_at=e.created_at,
        )
        for e in exams
    ]


@student_router.get("/slots", response_model=list[ExamSlotOut])
def list_open_slots(db: DbSession, exam_id: int, user: User = RequireStudent):
    """Open exam slots for a specific exam, scoped to the caller's college.
    Unlike /admin/exam-slots (staff-only), this is reachable by the 'student'
    role. `exam_id` is required — slots are per-exam, so without it a
    student would see every other exam's sittings mixed in."""
    student = _get_student_or_404(db, user)
    exam = db.execute(
        select(Exam).where(Exam.id == exam_id, Exam.college_id == student.college_id)
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    slots = db.execute(
        select(ExamSlot)
        .where(ExamSlot.exam_id == exam_id, ExamSlot.college_id == student.college_id, ExamSlot.status == "open")
        .order_by(ExamSlot.starts_at)
    ).scalars().all()
    return [_serialize_slot(db, s) for s in slots]


@student_router.post("/slots/{slot_id}/hold", response_model=SlotHoldOut, status_code=status.HTTP_201_CREATED)
def hold_slot(slot_id: int, db: DbSession, user: User = RequireStudent):
    """Atomically reserves a seat for SLOT_HOLD_MINUTES. Locks the slot row
    so concurrent requests can't oversell capacity; the actual capacity
    check re-counts confirmed registrations + other live holds under that
    lock before inserting."""
    student = _get_student_or_404(db, user)

    slot = db.execute(
        select(ExamSlot).where(ExamSlot.id == slot_id, ExamSlot.college_id == student.college_id).with_for_update()
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam slot not found")
    if slot.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This slot is not open for booking")
    if slot.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_409_CONFLICT, "This slot has already started")

    existing = db.execute(
        select(SlotHold).where(SlotHold.slot_id == slot.id, SlotHold.student_id == student.id)
    ).scalar_one_or_none()
    if existing is not None and existing.status == "held" and existing.expires_at > datetime.now(timezone.utc):
        return existing

    booked = _slot_booked_count(db, slot.id)
    if booked >= slot.max_capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "This slot is full")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=Settings.SLOT_HOLD_MINUTES)
    if existing is not None:
        existing.status = "held"
        existing.expires_at = expires_at
        existing.registration_id = None
        hold = existing
    else:
        hold = SlotHold(slot_id=slot.id, student_id=student.id, expires_at=expires_at, status="held")
        db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold


@student_router.delete("/slots/{slot_id}/hold", status_code=status.HTTP_204_NO_CONTENT)
def release_hold(slot_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    hold = db.execute(
        select(SlotHold).where(SlotHold.slot_id == slot_id, SlotHold.student_id == student.id, SlotHold.status == "held")
    ).scalar_one_or_none()
    if hold is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active hold on this slot")
    hold.status = "released"
    db.commit()


@student_router.post("/registrations", response_model=ExamRegistrationOut, status_code=status.HTTP_201_CREATED)
def create_registration(payload: RegistrationCreate, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)

    exam = db.execute(
        select(Exam).where(Exam.id == payload.exam_id, Exam.college_id == student.college_id)
    ).scalar_one_or_none()
    if exam is None or exam.status != "published":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Exam not found or not open for registration")

    hold = db.execute(
        select(SlotHold).where(SlotHold.id == payload.hold_id, SlotHold.student_id == student.id)
    ).scalar_one_or_none()
    if hold is None or hold.status != "held" or hold.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Hold is invalid or has expired — book the slot again")

    is_free = not exam.fee or exam.fee <= 0
    now = datetime.now(timezone.utc)
    reg = ExamRegistration(
        college_id=student.college_id,
        student_id=student.id,
        exam_id=exam.id,
        slot_id=hold.slot_id,
        registration_number=f"REG-{exam.id}-{uuid_lib.uuid4().hex[:8].upper()}",
        status="confirmed" if is_free else "pending_payment",
        registered_at=now,
        confirmed_at=now if is_free else None,
    )
    db.add(reg)
    db.flush()
    hold.status = "converted"
    hold.registration_id = reg.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You are already registered for this exam")

    reg = db.execute(
        select(ExamRegistration).where(ExamRegistration.id == reg.id).options(selectinload(ExamRegistration.exam))
    ).scalar_one()

    # Confirmation mail goes out immediately for free exams (already
    # "confirmed" above); paid exams get theirs from verify_payment() once
    # the payment actually clears.
    if reg.status == "confirmed":
        send_registration_confirmation(
            to_email=student.email,
            student_name=student.profile.name if student.profile else (user.username or "Student"),
            exam_name=reg.exam.name,
            registration_number=reg.registration_number,
            exam_starts_at=reg.exam.starts_at,
            fee_paid=False,
        )
    return _serialize_registration(reg)


@student_router.get("/registrations", response_model=list[ExamRegistrationOut])
def list_my_registrations(db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    regs = db.execute(
        select(ExamRegistration)
        .where(ExamRegistration.student_id == student.id)
        .options(selectinload(ExamRegistration.exam))
        .order_by(ExamRegistration.id.desc())
    ).scalars().all()
    return [_serialize_registration(r) for r in regs]


def _get_own_registration_or_404(db: DbSession, registration_id: int, student: Student) -> ExamRegistration:
    reg = db.execute(
        select(ExamRegistration)
        .where(ExamRegistration.id == registration_id, ExamRegistration.student_id == student.id)
        .options(selectinload(ExamRegistration.exam))
    ).scalar_one_or_none()
    if reg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registration not found")
    return reg


@student_router.get("/registrations/{registration_id}", response_model=ExamRegistrationOut)
def get_my_registration(registration_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    return _serialize_registration(_get_own_registration_or_404(db, registration_id, student))


@student_router.delete("/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_registration(registration_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    reg = _get_own_registration_or_404(db, registration_id, student)
    if reg.status not in ("pending_payment", "payment_failed"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only unpaid registrations can be self-cancelled — contact your college for a confirmed booking",
        )
    reg.status = "cancelled"
    db.commit()


@student_router.post("/registrations/{registration_id}/payment-order", response_model=PaymentOrderOut)
async def create_payment_order(registration_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    reg = _get_own_registration_or_404(db, registration_id, student)
    if reg.status != "pending_payment":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This registration does not have a pending payment")
    if not reg.exam.fee or reg.exam.fee <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This exam has no fee to pay")

    order = await create_order(
        amount=reg.exam.fee,
        currency=reg.exam.fee_currency,
        receipt=f"reg-{reg.id}",
    )
    payment = Payment(
        college_id=reg.college_id,
        registration_id=reg.id,
        provider="razorpay",
        order_id=order["id"],
        amount=reg.exam.fee,
        currency=reg.exam.fee_currency,
        status="created",
        raw_response=order,
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A payment order already exists for this registration")
    db.refresh(payment)
    return PaymentOrderOut(
        payment_id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        key_id=Settings.RAZORPAY_KEY_ID or None,
    )


def _finalize_paid_registration(db: DbSession, reg: ExamRegistration, student: Student, user: User) -> ExamRegistrationOut:
    """Shared by verify_payment() and mock_confirm_payment(): flips the
    registration to confirmed, sends the confirmation mail, and (if enabled)
    auto-provisions the exam invitation."""
    reg.status = "confirmed"
    reg.confirmed_at = datetime.now(timezone.utc)
    db.commit()

    send_registration_confirmation(
        to_email=student.email,
        student_name=student.profile.name if student.profile else (user.username or "Student"),
        exam_name=reg.exam.name,
        registration_number=reg.registration_number,
        exam_starts_at=reg.exam.starts_at,
        fee_paid=True,
    )

    # Invitation delivery is admin-controlled by default. Set
    # AUTO_SEND_EXAM_INVITATION=true only if automatic delivery is desired.
    if Settings.AUTO_SEND_EXAM_INVITATION:
        provisioned = _provision_invitation(db, reg)
    else:
        provisioned = None
    if provisioned:
        invitation, token, target_user, invite_student = provisioned
        db.commit()
        sent = send_exam_invitation(
            to_email=(target_user.email if target_user and target_user.email else invite_student.email),
            student_name=invite_student.profile.name if invite_student.profile else (target_user.username if target_user else "Student"),
            exam_name=reg.exam.name,
            exam_starts_at=reg.exam.starts_at,
            invitation_url=f"{Settings.FRONTEND_URL.rstrip('/')}/redeem-invitation?token={token}",
            expires_at=invitation.expires_at,
        )
        if sent:
            invitation.status = "sent"; invitation.sent_at = datetime.now(timezone.utc); db.commit()

    reg = db.execute(
        select(ExamRegistration).where(ExamRegistration.id == reg.id).options(selectinload(ExamRegistration.exam))
    ).scalar_one()
    return _serialize_registration(reg)


@student_router.post("/payments/verify", response_model=ExamRegistrationOut)
def verify_payment(payload: PaymentVerify, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    reg = _get_own_registration_or_404(db, payload.registration_id, student)

    payment = db.execute(
        select(Payment).where(Payment.registration_id == reg.id, Payment.order_id == payload.razorpay_order_id)
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No matching payment order for this registration")

    ok = verify_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not ok:
        payment.status = "failed"
        reg.status = "payment_failed"
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment signature verification failed")

    payment.payment_id = payload.razorpay_payment_id
    payment.signature = payload.razorpay_signature
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    return _finalize_paid_registration(db, reg, student, user)


@student_router.post("/registrations/{registration_id}/payments/mock-confirm", response_model=ExamRegistrationOut)
def mock_confirm_payment(registration_id: int, db: DbSession, user: User = RequireStudent):
    """Dev/local-only stand-in for the Razorpay checkout round-trip. The
    frontend only calls this when POST .../payment-order came back with
    key_id=null (i.e. RAZORPAY_KEY_ID/SECRET aren't configured — see
    utils/payments.is_live()), so there is no real checkout widget to open.
    Refuses to run once real Razorpay credentials are set, so this can never
    be used to skip payment in production."""
    if is_live():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Razorpay is live for this deployment — use the real checkout flow")

    student = _get_student_or_404(db, user)
    reg = _get_own_registration_or_404(db, registration_id, student)
    if reg.status != "pending_payment":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This registration does not have a pending payment")

    payment = db.execute(
        select(Payment)
        .where(Payment.registration_id == reg.id, Payment.status == "created")
        .order_by(Payment.id.desc())
    ).scalars().first()
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending payment order for this registration — create one first")

    payment.payment_id = f"mock_pay_{uuid_lib.uuid4().hex[:16]}"
    payment.signature = "mock"
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    return _finalize_paid_registration(db, reg, student, user)


# ==================================================================
# Admin/staff: view registrations & payments, generate invitations
# ==================================================================

@admin_router.get("/exams/{exam_id}/registrations", response_model=list[ExamRegistrationOut])
def list_exam_registrations(
    exam_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    status_: Optional[str] = None,
):
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    stmt = (
        select(ExamRegistration)
        .where(ExamRegistration.exam_id == exam.id)
        .options(selectinload(ExamRegistration.exam))
    )
    if status_ is not None:
        stmt = stmt.where(ExamRegistration.status == status_)
    regs = db.execute(stmt.order_by(ExamRegistration.id.desc())).scalars().all()
    return [_serialize_registration(r) for r in regs]


@admin_router.get("/exams/{exam_id}/payments", response_model=list[PaymentOut])
def list_exam_payments(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    rows = db.execute(
        select(Payment)
        .join(ExamRegistration, Payment.registration_id == ExamRegistration.id)
        .where(ExamRegistration.exam_id == exam.id)
        .order_by(Payment.id.desc())
    ).scalars().all()
    return rows


# ------------------------------------------------------------- invitations

def _generate_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def _generate_username(db: DbSession, base: str) -> str:
    base = base or "student"
    candidate = base
    suffix = 0
    while db.execute(select(User).where(User.username == candidate)).scalar_one_or_none() is not None:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def _provision_invitation(db: DbSession, reg: ExamRegistration, expires_in_hours: int = 72):
    """Create the one-time login invitation for a confirmed registration."""
    existing = db.execute(select(ExamInvitation).where(ExamInvitation.registration_id == reg.id)).scalar_one_or_none()
    if existing is not None:
        return None
    student = db.get(Student, reg.student_id)
    role = db.execute(select(Role).where(Role.name == "student")).scalar_one_or_none()
    if not student or not role:
        return None
    if student.user_id is None:
        username = _generate_username(db, student.application_number or student.register_number or f"stu{student.id}")
        new_user = User(college_id=student.college_id, profile_id=student.profile_id, email=student.email,
                        role_id=role.id, username=username, password_hash=hash_password(secrets.token_urlsafe(9)), is_active=True)
        db.add(new_user); db.flush(); student.user_id = new_user.id
    target_user = db.get(User, student.user_id)
    token, token_hash = _generate_token()
    invitation = ExamInvitation(exam_id=reg.exam_id, student_id=student.id, registration_id=reg.id,
                                user_id=student.user_id, exam_token_hash=token_hash,
                                expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours), status="pending")
    db.add(invitation); db.flush()
    return invitation, token, target_user, student


@admin_router.post(
    "/exams/{exam_id}/invitations/generate",
    response_model=list[ExamInvitationWithToken],
    status_code=status.HTTP_201_CREATED,
)
def generate_invitations(
    exam_id: int,
    payload: InvitationGenerate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    """Provisions a login (users row, role=student) for each confirmed
    registration that doesn't already have one, and issues an invitation
    token. The plaintext token is only ever returned here — only its hash
    is persisted — so the caller must deliver it now."""
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")

    stmt = (
        select(ExamRegistration)
        .where(ExamRegistration.exam_id == exam.id, ExamRegistration.status == "confirmed")
        .options(selectinload(ExamRegistration.student))
    )
    if payload.registration_ids:
        stmt = stmt.where(ExamRegistration.id.in_(payload.registration_ids))
    registrations = db.execute(stmt).scalars().all()

    already_invited = {
        r[0]
        for r in db.execute(
            select(ExamInvitation.registration_id).where(ExamInvitation.exam_id == exam.id)
        ).all()
        if r[0] is not None
    }

    student_role = db.execute(select(Role).where(Role.name == "student")).scalar_one_or_none()
    if student_role is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Role 'student' is not seeded")

    results: list[ExamInvitationWithToken] = []
    mail_jobs = []
    expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)

    for reg in registrations:
        if reg.id in already_invited:
            continue
        student = reg.student

        if student.user_id is None:
            base_username = (student.application_number or student.register_number or f"stu{student.id}").lower()
            base_username = "".join(c for c in base_username if c.isalnum()) or f"stu{student.id}"
            username = _generate_username(db, base_username)
            temp_password = secrets.token_urlsafe(9)
            new_user = User(
                college_id=student.college_id,
                profile_id=student.profile_id,
                email=student.email,
                role_id=student_role.id,
                username=username,
                password_hash=hash_password(temp_password),
                is_active=True,
            )
            db.add(new_user)
            db.flush()
            student.user_id = new_user.id
            user_id = new_user.id
            username_out = username
        else:
            user_id = student.user_id
            existing_user = db.get(User, user_id)
            username_out = existing_user.username if existing_user else None

        token, token_hash = _generate_token()
        invitation = ExamInvitation(
            exam_id=exam.id,
            student_id=student.id,
            registration_id=reg.id,
            user_id=user_id,
            exam_token_hash=token_hash,
            sent_at=None,
            expires_at=expires_at,
            status="pending",
        )
        db.add(invitation)
        db.flush()
        results.append(
            ExamInvitationWithToken(
                id=invitation.id,
                exam_id=invitation.exam_id,
                student_id=invitation.student_id,
                registration_id=invitation.registration_id,
                user_id=invitation.user_id,
                username=username_out,
                sent_at=invitation.sent_at,
                expires_at=invitation.expires_at,
                status=invitation.status,
                created_at=invitation.created_at,
                token=token,
            )
        )
        mail_jobs.append((invitation, token, student, db.get(User, user_id)))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Failed to generate one or more invitations — try again")
    for invitation, token, student, target_user in mail_jobs:
        if send_exam_invitation(
            to_email=(target_user.email if target_user and target_user.email else student.email),
            student_name=student.profile.name if student.profile else (target_user.username if target_user else "Student"),
            exam_name=exam.name, exam_starts_at=exam.starts_at,
            invitation_url=f"{Settings.FRONTEND_URL.rstrip('/')}/redeem-invitation?token={token}",
            expires_at=invitation.expires_at,
        ):
            invitation.status = "sent"; invitation.sent_at = datetime.now(timezone.utc)
    db.commit()
    return results


@admin_router.get("/exams/{exam_id}/invitations", response_model=list[ExamInvitationOut])
def list_invitations(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    rows = db.execute(
        select(ExamInvitation, User.username)
        .join(User, User.id == ExamInvitation.user_id, isouter=True)
        .where(ExamInvitation.exam_id == exam.id)
        .order_by(ExamInvitation.id.desc())
    ).all()
    return [
        ExamInvitationOut(
            id=inv.id, exam_id=inv.exam_id, student_id=inv.student_id, registration_id=inv.registration_id,
            user_id=inv.user_id, username=username, sent_at=inv.sent_at, expires_at=inv.expires_at,
            status=inv.status, created_at=inv.created_at,
        )
        for inv, username in rows
    ]


@admin_router.post("/invitations/{invitation_id}/resend", response_model=ExamInvitationWithToken)
def resend_invitation(invitation_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    invitation = db.execute(
        select(ExamInvitation)
        .join(Exam, Exam.id == ExamInvitation.exam_id)
        .where(ExamInvitation.id == invitation_id, Exam.college_id == user.college_id)
    ).scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    if invitation.status == "used":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invitation has already been used")

    token, token_hash = _generate_token()
    invitation.exam_token_hash = token_hash
    invitation.status = "sent"
    invitation.sent_at = datetime.now(timezone.utc)
    invitation.expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
    db.commit()

    target_user = db.get(User, invitation.user_id) if invitation.user_id else None
    invite_student = db.get(Student, invitation.student_id)
    send_exam_invitation(
        to_email=(target_user.email if target_user and target_user.email else (invite_student.email if invite_student else None)),
        student_name=invite_student.profile.name if invite_student and invite_student.profile else (target_user.username if target_user else "Student"),
        exam_name=invitation.exam.name, exam_starts_at=invitation.exam.starts_at,
        invitation_url=f"{Settings.FRONTEND_URL.rstrip('/')}/redeem-invitation?token={token}",
        expires_at=invitation.expires_at,
    )
    return ExamInvitationWithToken(
        id=invitation.id, exam_id=invitation.exam_id, student_id=invitation.student_id,
        registration_id=invitation.registration_id, user_id=invitation.user_id,
        username=target_user.username if target_user else None,
        sent_at=invitation.sent_at, expires_at=invitation.expires_at, status=invitation.status,
        created_at=invitation.created_at, token=token,
    )
