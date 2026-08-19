import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import DbSession
from core.security import create_access_token, create_refresh_token, hash_password
from core.settings import Settings
from models.auth import Profile, Role, User
from models.college import College
from models.entrance import ExamSlot
from models.exam import Exam
from models.student import Student
from models.verification import OtpVerification
from schemas.exam import ExamPublicOut
from schemas.verification import (
    ApplicantSignupRequest,
    ApplicantSignupResponse,
    PublicCollegeOut,
    SendOtpRequest,
    SendOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from utils.email import send_otp_email
from utils.sms import send_sms

router = APIRouter(prefix="/public", tags=["public-signup"])
log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def _normalize_contact(contact_type: str, contact: str) -> str:
    contact = contact.strip()
    if contact_type == "email":
        contact = contact.lower()
        if not _EMAIL_RE.match(contact):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That doesn't look like a valid email address")
        return contact
    # phone
    digits_only = re.sub(r"[\s\-()]", "", contact)
    if not _PHONE_RE.match(digits_only):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That doesn't look like a valid phone number")
    return digits_only


def _hash_code(code: str, contact: str) -> str:
    return hashlib.sha256(f"{code}:{contact}:{Settings.JWT_SECRET}".encode()).hexdigest()


def _generate_code() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(Settings.OTP_LENGTH))


# ------------------------------------------------------------------ colleges

@router.get("/colleges", response_model=list[PublicCollegeOut])
def list_public_colleges(db: DbSession):
    """Active colleges an applicant can pick from on the public signup form.
    Deliberately returns only display fields — no internal ids like `code`
    beyond `id`, no contact emails/phones."""
    colleges = db.execute(
        select(College).where(College.is_active.is_(True)).order_by(College.name)
    ).scalars().all()
    return [PublicCollegeOut(id=c.id, name=c.name, city=c.city, state=c.state) for c in colleges]


# ---------------------------------------------------------------- exam link

@router.get("/exams/{slug}", response_model=ExamPublicOut)
def get_public_exam(slug: str, db: DbSession):
    """Landing page for the exam's shareable link (WhatsApp/poster/QR/portal):
    FRONTEND_URL/e/{slug}. Unauthenticated by design — the frontend uses this
    to show exam details and a "Register" button that sends the applicant
    into OTP signup / login, with this exam preselected."""
    exam = db.execute(
        select(Exam)
        .where(Exam.public_slug == slug, Exam.status.in_(("published", "running")))
        .options(selectinload(Exam.exam_type))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This exam link is invalid or no longer active")

    college = db.get(College, exam.college_id)
    open_slots = db.execute(
        select(func.count(ExamSlot.id)).where(ExamSlot.exam_id == exam.id, ExamSlot.status == "open")
    ).scalar_one()

    return ExamPublicOut(
        name=exam.name,
        description=exam.description,
        exam_type_name=exam.exam_type.name if exam.exam_type else None,
        college_name=college.name if college else "",
        starts_at=exam.starts_at,
        ends_at=exam.ends_at,
        duration_minutes=exam.duration_minutes,
        fee=exam.fee,
        fee_currency=exam.fee_currency,
        status=exam.status,
        open_slot_count=open_slots,
    )


# ----------------------------------------------------------------------- otp

@router.post("/signup/send-otp", response_model=SendOtpResponse)
def send_otp(payload: SendOtpRequest, db: DbSession):
    contact = _normalize_contact(payload.contact_type, payload.contact)

    recent = db.execute(
        select(OtpVerification)
        .where(
            OtpVerification.contact_type == payload.contact_type,
            OtpVerification.contact == contact,
            OtpVerification.purpose == "signup",
        )
        .order_by(OtpVerification.id.desc())
    ).scalars().first()
    if recent is not None:
        elapsed = (datetime.now(timezone.utc) - recent.created_at).total_seconds()
        if elapsed < Settings.OTP_RESEND_SECONDS:
            wait = int(Settings.OTP_RESEND_SECONDS - elapsed)
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Please wait {wait}s before requesting another code")

    code = _generate_code()
    row = OtpVerification(
        contact_type=payload.contact_type,
        contact=contact,
        purpose="signup",
        code_hash=_hash_code(code, contact),
        attempts=0,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=Settings.OTP_EXPIRE_MINUTES),
    )
    db.add(row)
    db.commit()

    if payload.contact_type == "email":
        delivered = send_otp_email(to_email=contact, code=code, expires_in_minutes=Settings.OTP_EXPIRE_MINUTES)
    else:
        delivered = send_sms(to_phone=contact, message=f"Your verification code is {code}. It expires in {Settings.OTP_EXPIRE_MINUTES} minutes.")

    return SendOtpResponse(
        contact_type=payload.contact_type,
        contact=contact,
        expires_in_seconds=Settings.OTP_EXPIRE_MINUTES * 60,
        # Only handed back when nothing was actually delivered (no SMTP/SMS
        # configured), so local/dev testing doesn't need a real inbox or phone.
        debug_code=None if delivered else code,
    )


@router.post("/signup/verify-otp", response_model=VerifyOtpResponse)
def verify_otp(payload: VerifyOtpRequest, db: DbSession):
    contact = _normalize_contact(payload.contact_type, payload.contact)

    row = db.execute(
        select(OtpVerification)
        .where(
            OtpVerification.contact_type == payload.contact_type,
            OtpVerification.contact == contact,
            OtpVerification.purpose == "signup",
            OtpVerification.verified_at.is_(None),
        )
        .order_by(OtpVerification.id.desc())
    ).scalars().first()

    if row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No pending code for this contact — request a new one")
    if row.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This code has expired — request a new one")
    if row.attempts >= Settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Too many incorrect attempts — request a new code")

    if row.code_hash != _hash_code(payload.code.strip(), contact):
        row.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect code")

    row.verified_at = datetime.now(timezone.utc)
    db.commit()
    return VerifyOtpResponse(contact_type=payload.contact_type, contact=contact, verified=True)


def _is_verified(db: DbSession, contact_type: str, contact: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=Settings.OTP_VERIFIED_TTL_MINUTES)
    row = db.execute(
        select(OtpVerification)
        .where(
            OtpVerification.contact_type == contact_type,
            OtpVerification.contact == contact,
            OtpVerification.purpose == "signup",
            OtpVerification.verified_at.is_not(None),
            OtpVerification.verified_at >= cutoff,
        )
        .order_by(OtpVerification.id.desc())
    ).scalars().first()
    return row is not None


# ------------------------------------------------------------------- signup

def _generate_username(db: DbSession, base: str) -> str:
    base = "".join(c for c in base.lower() if c.isalnum()) or "applicant"
    candidate = base
    suffix = 0
    while db.execute(select(User).where(User.username == candidate)).scalar_one_or_none() is not None:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


@router.post("/signup/register", response_model=ApplicantSignupResponse, status_code=status.HTTP_201_CREATED)
def register_applicant(payload: ApplicantSignupRequest, db: DbSession):
    """Self-service applicant signup. Requires both the email and phone to
    already have a verified OTP (via /public/signup/verify-otp) for this
    exact contact value within the last OTP_VERIFIED_TTL_MINUTES."""
    college = db.execute(
        select(College).where(College.id == payload.college_id, College.is_active.is_(True))
    ).scalar_one_or_none()
    if college is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected college is not available")

    email = _normalize_contact("email", payload.email)
    phone = _normalize_contact("phone", payload.phone)

    if not _is_verified(db, "email", email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please verify your email first")
    if not _is_verified(db, "phone", phone):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Please verify your phone number first")

    existing = db.execute(
        select(Student).where(Student.college_id == college.id, Student.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An application already exists for this email at this college")

    student_role = db.execute(select(Role).where(Role.name == "student")).scalar_one_or_none()
    if student_role is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Role 'student' is not seeded")

    profile = Profile(name=payload.name, phone=phone, dob=payload.dob, gender=payload.gender)
    db.add(profile)
    db.flush()

    username = _generate_username(db, email.split("@")[0])
    new_user = User(
        college_id=college.id,
        profile_id=profile.id,
        role_id=student_role.id,
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    student = Student(
        college_id=college.id,
        user_id=new_user.id,
        profile_id=profile.id,
        email=email,
        stage="applicant",
        tenth_mark=payload.tenth_mark,
        twelfth_mark=payload.twelfth_mark,
        is_diploma=False,
    )
    db.add(student)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with these details already exists")

    return ApplicantSignupResponse(
        access_token=create_access_token(new_user.id),
        refresh_token=create_refresh_token(new_user.id),
        username=new_user.username,
        student_id=student.id,
    )
