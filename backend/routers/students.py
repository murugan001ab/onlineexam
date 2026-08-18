from datetime import datetime, timezone
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from core.security import hash_password
from models.auth import Profile, Role, User
from models.organization import Class
from models.student import Student, StudentClass
from schemas.student import (
    StudentClassAssign,
    StudentClassOut,
    StudentCreate,
    StudentLoginCreate,
    StudentLoginOut,
    StudentLoginUpdate,
    StudentOut,
    StudentUpdate,
)

router = APIRouter(prefix="/admin/students", tags=["students"])

RequireStaff = Depends(require_roles(*STAFF_ROLES))


def _serialize(student: Student) -> StudentOut:
    return StudentOut(
        id=student.id,
        college_id=student.college_id,
        register_number=student.register_number,
        application_number=student.application_number,
        stage=student.stage,
        tenth_mark=student.tenth_mark,
        twelfth_mark=student.twelfth_mark,
        diploma_mark=student.diploma_mark,
        is_diploma=student.is_diploma,
        admitted_at=student.admitted_at,
        has_login=student.user_id is not None,
        profile=student.profile,
    )


def _get_student_or_404(db: DbSession, student_id: int, college_id: int) -> Student:
    student = db.execute(
        select(Student)
        .where(Student.id == student_id, Student.college_id == college_id)
        .options(selectinload(Student.profile))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    return student


@router.get("", response_model=list[StudentOut])
def list_students(
    db: DbSession,
    user: User = RequireStaff,
    stage: Optional[str] = None,
    is_diploma: Optional[bool] = None,
    q: Optional[str] = None,
):
    """q matches register_number, application_number, or profile name (prefix, case-insensitive)."""
    stmt = (
        select(Student)
        .where(Student.college_id == user.college_id)
        .options(selectinload(Student.profile))
    )
    if stage is not None:
        if stage not in ("applicant", "enrolled"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "stage must be 'applicant' or 'enrolled'")
        stmt = stmt.where(Student.stage == stage)
    if is_diploma is not None:
        stmt = stmt.where(Student.is_diploma == is_diploma)
    if q:
        like = f"{q}%"
        stmt = stmt.join(Profile, Profile.id == Student.profile_id, isouter=True).where(
            (Student.register_number.ilike(like))
            | (Student.application_number.ilike(like))
            | (Profile.name.ilike(like))
        )
    students = db.execute(stmt.order_by(Student.id.desc())).scalars().all()
    return [_serialize(s) for s in students]


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: DbSession, user: User = RequireStaff):
    return _serialize(_get_student_or_404(db, student_id, user.college_id))


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: DbSession, user: User = RequireStaff):
    if user.college_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This account is not tied to a college")

    profile = Profile(**payload.profile.model_dump())
    db.add(profile)
    db.flush()

    student = Student(
        college_id=user.college_id,
        profile_id=profile.id,
        register_number=payload.register_number,
        application_number=payload.application_number,
        stage=payload.stage,
        tenth_mark=payload.tenth_mark,
        twelfth_mark=payload.twelfth_mark,
        diploma_mark=payload.diploma_mark,
        is_diploma=payload.is_diploma,
        admitted_at=datetime.now(timezone.utc) if payload.stage == "enrolled" else None,
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A student with this register_number or application_number already exists for this college",
        )
    db.refresh(student)
    student.profile = profile
    return _serialize(student)


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: DbSession, user: User = RequireStaff):
    student = _get_student_or_404(db, student_id, user.college_id)
    data = payload.model_dump(exclude_unset=True, exclude={"profile"})

    if data.get("stage") == "enrolled" and student.stage != "enrolled" and "admitted_at" not in data:
        data["admitted_at"] = datetime.now(timezone.utc)

    for field, value in data.items():
        setattr(student, field, value)

    if payload.profile is not None:
        profile_data = payload.profile.model_dump(exclude_unset=True)
        if student.profile is None:
            student.profile = Profile(name=profile_data.get("name", "Unnamed"))
            db.add(student.profile)
        for field, value in profile_data.items():
            setattr(student.profile, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A student with this register_number or application_number already exists for this college",
        )
    db.refresh(student)
    return _serialize(student)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: DbSession, user: User = RequireStaff):
    """Hard delete: students have no is_active flag. Blocked once the student
    has registrations, class enrollments, or attempts on record — those carry
    real history that shouldn't silently vanish. Having a login (user_id set)
    does not by itself block deletion, but deactivate the login first via
    PATCH /{student_id}/login if the student is being removed for good."""
    student = _get_student_or_404(db, student_id, user.college_id)
    db.delete(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Student has registrations, class enrollments, or attempts on record — remove those first",
        )


# ------------------------------------------------------------------ classes

@router.get("/{student_id}/classes", response_model=list[StudentClassOut])
def list_student_classes(student_id: int, db: DbSession, user: User = RequireStaff, include_left: bool = False):
    student = _get_student_or_404(db, student_id, user.college_id)
    stmt = (
        select(StudentClass)
        .where(StudentClass.student_id == student.id)
        .options(selectinload(StudentClass.class_))
    )
    if not include_left:
        stmt = stmt.where(StudentClass.left_at.is_(None))
    rows = db.execute(stmt).scalars().all()
    return [
        StudentClassOut(
            id=r.id, class_id=r.class_id, class_name=r.class_.name,
            academic_year=r.academic_year, joined_at=r.joined_at, left_at=r.left_at,
        )
        for r in rows
    ]


@router.post("/{student_id}/classes", response_model=StudentClassOut, status_code=status.HTTP_201_CREATED)
def enroll_student_in_class(
    student_id: int, payload: StudentClassAssign, db: DbSession, user: User = RequireStaff
):
    student = _get_student_or_404(db, student_id, user.college_id)
    klass = db.execute(
        select(Class).where(Class.id == payload.class_id, Class.college_id == user.college_id)
    ).scalar_one_or_none()
    if klass is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "class_id does not exist for this college")

    existing = db.execute(
        select(StudentClass).where(
            StudentClass.student_id == student.id, StudentClass.class_id == klass.id
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing is not None:
        if existing.left_at is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Student is already enrolled in this class")
        existing.left_at = None
        existing.joined_at = now
        existing.academic_year = payload.academic_year
        db.commit()
        row = existing
    else:
        row = StudentClass(
            student_id=student.id, class_id=klass.id,
            academic_year=payload.academic_year, joined_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    return StudentClassOut(
        id=row.id, class_id=row.class_id, class_name=klass.name,
        academic_year=row.academic_year, joined_at=row.joined_at, left_at=row.left_at,
    )


@router.delete("/{student_id}/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_from_class(student_id: int, class_id: int, db: DbSession, user: User = RequireStaff):
    """Marks left_at rather than deleting — preserves enrollment history."""
    student = _get_student_or_404(db, student_id, user.college_id)
    row = db.execute(
        select(StudentClass).where(
            StudentClass.student_id == student.id, StudentClass.class_id == class_id, StudentClass.left_at.is_(None)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active enrollment not found")
    row.left_at = datetime.now(timezone.utc)
    db.commit()


# --------------------------------------------------------------------- login

def _generate_username(db: DbSession, base: str) -> str:
    base = "".join(c for c in (base or "student").lower() if c.isalnum()) or "student"
    candidate = base
    suffix = 0
    while db.execute(select(User).where(User.username == candidate)).scalar_one_or_none() is not None:
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


@router.post("/{student_id}/login", response_model=StudentLoginOut, status_code=status.HTTP_201_CREATED)
def provision_student_login(
    student_id: int, payload: StudentLoginCreate, db: DbSession, user: User = RequireStaff
):
    """Creates the users row (role=student) for a student who doesn't have one
    yet. This is the general-purpose path for students who need a login for
    class quizzes/training and aren't going through exam registration — the
    exam-invitation flow (routers/registration.py) does the same thing for
    entrance-exam registrants and will detect and reuse an existing login."""
    student = _get_student_or_404(db, student_id, user.college_id)
    if student.user_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This student already has a login")

    student_role = db.execute(select(Role).where(Role.name == "student")).scalar_one_or_none()
    if student_role is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Role 'student' is not seeded")

    if payload.username:
        if db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken")
        username = payload.username
    else:
        base = student.register_number or student.application_number or (student.profile.name if student.profile else None)
        username = _generate_username(db, base)

    temp_password = secrets.token_urlsafe(9)
    new_user = User(
        college_id=student.college_id,
        profile_id=student.profile_id,
        role_id=student_role.id,
        username=username,
        password_hash=hash_password(temp_password),
        is_active=True,
    )
    db.add(new_user)
    db.flush()
    student.user_id = new_user.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is already taken")

    return StudentLoginOut(
        user_id=new_user.id, username=new_user.username, is_active=new_user.is_active,
        temporary_password=temp_password,
    )


@router.get("/{student_id}/login", response_model=StudentLoginOut)
def get_student_login(student_id: int, db: DbSession, user: User = RequireStaff):
    student = _get_student_or_404(db, student_id, user.college_id)
    if student.user_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This student has no login yet")
    login_user = db.get(User, student.user_id)
    return StudentLoginOut(user_id=login_user.id, username=login_user.username, is_active=login_user.is_active)


@router.patch("/{student_id}/login", response_model=StudentLoginOut)
def update_student_login(
    student_id: int, payload: StudentLoginUpdate, db: DbSession, user: User = RequireStaff
):
    student = _get_student_or_404(db, student_id, user.college_id)
    if student.user_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This student has no login yet — provision one first")
    login_user = db.get(User, student.user_id)

    temp_password = None
    if payload.is_active is not None:
        login_user.is_active = payload.is_active
    if payload.reset_password:
        temp_password = secrets.token_urlsafe(9)
        login_user.password_hash = hash_password(temp_password)
    db.commit()

    return StudentLoginOut(
        user_id=login_user.id, username=login_user.username, is_active=login_user.is_active,
        temporary_password=temp_password,
    )
