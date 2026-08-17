from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import AdminOrSuperAdmin, DbSession, SuperAdmin
from core.security import hash_password
from models.auth import Profile, Role, User
from models.college import College
from schemas.college import CollegeCreate, CollegeOut, CollegeUpdate
from schemas.user import ProfileOut, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------- colleges

def _get_college_or_404(db: DbSession, college_id: int) -> College:
    college = db.get(College, college_id)
    if college is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "College not found")
    return college


@router.get("/colleges", response_model=list[CollegeOut])
def list_colleges(
    db: DbSession,
    user: User = SuperAdmin,
    is_active: Optional[bool] = None,
):
    stmt = select(College)
    if is_active is not None:
        stmt = stmt.where(College.is_active == is_active)
    return db.execute(stmt.order_by(College.name)).scalars().all()


@router.get("/colleges/{college_id}", response_model=CollegeOut)
def get_college(college_id: int, db: DbSession, user: User = SuperAdmin):
    return _get_college_or_404(db, college_id)


@router.post("/colleges", response_model=CollegeOut, status_code=status.HTTP_201_CREATED)
def create_college(payload: CollegeCreate, db: DbSession, user: User = SuperAdmin):
    college = College(**payload.model_dump())
    db.add(college)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "College code already exists")
    db.refresh(college)
    return college


@router.patch("/colleges/{college_id}", response_model=CollegeOut)
def update_college(college_id: int, payload: CollegeUpdate, db: DbSession, user: User = SuperAdmin):
    college = _get_college_or_404(db, college_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(college, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "College code already exists")
    db.refresh(college)
    return college


@router.delete("/colleges/{college_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_college(college_id: int, db: DbSession, user: User = SuperAdmin):
    """Soft delete: colleges are referenced by users, departments, classes,
    students etc., so a hard delete would fail or orphan rows."""
    college = _get_college_or_404(db, college_id)
    college.is_active = False
    db.commit()


# --------------------------------------------------------------- admin/staff users

def _get_role_or_500(db: DbSession, role_name: str) -> Role:
    role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Role '{role_name}' is not seeded — run alembic migrations",
        )
    return role


def _load_options():
    return (selectinload(User.profile), selectinload(User.role))


def _serialize(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        username=u.username,
        email=u.email,
        role=u.role.name,
        college_id=u.college_id,
        is_active=u.is_active,
        last_login_at=u.last_login_at,
        created_at=u.created_at,
        profile=ProfileOut.model_validate(u.profile, from_attributes=True) if u.profile else None,
    )


def _get_managed_user_or_404(db: DbSession, user_id: int, requester: User) -> User:
    """Fetch a user this requester is allowed to manage: super_admin can see
    any admin/staff; admin can only see staff in their own college."""
    stmt = (
        select(User)
        .join(Role)
        .where(User.id == user_id, Role.name.in_(("admin", "staff")))
        .options(*_load_options())
    )
    if requester.role.name == "admin":
        stmt = stmt.where(Role.name == "staff", User.college_id == requester.college_id)
    target = db.execute(stmt).scalar_one_or_none()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return target


def _authorize_create(requester: User, payload: UserCreate) -> int:
    """Returns the college_id to use, or raises 403/400."""
    if requester.role.name == "super_admin":
        if payload.college_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "college_id is required")
        return payload.college_id
    # requester is admin
    if payload.role != "staff":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins can only create staff accounts")
    return requester.college_id


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: DbSession,
    user: User = AdminOrSuperAdmin,
    role: Optional[str] = None,
    college_id: Optional[int] = None,
    is_active: Optional[bool] = None,
):
    stmt = select(User).join(Role).where(Role.name.in_(("admin", "staff"))).options(*_load_options())
    if user.role.name == "admin":
        stmt = stmt.where(Role.name == "staff", User.college_id == user.college_id)
    elif college_id is not None:
        stmt = stmt.where(User.college_id == college_id)
    if role is not None:
        if role not in ("admin", "staff"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be 'admin' or 'staff'")
        stmt = stmt.where(Role.name == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    users = db.execute(stmt.order_by(User.username)).scalars().all()
    return [_serialize(u) for u in users]


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    return _serialize(_get_managed_user_or_404(db, user_id, user))


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, user: User = AdminOrSuperAdmin):
    college_id = _authorize_create(user, payload)
    if not db.get(College, college_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "college_id does not exist")

    role = _get_role_or_500(db, payload.role)
    profile = Profile(**payload.profile.model_dump())
    db.add(profile)
    db.flush()

    new_user = User(
        college_id=college_id,
        profile_id=profile.id,
        role_id=role.id,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")

    stmt = select(User).where(User.id == new_user.id).options(*_load_options())
    return _serialize(db.execute(stmt).scalar_one())


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: DbSession, user: User = AdminOrSuperAdmin):
    target = _get_managed_user_or_404(db, user_id, user)

    if payload.college_id is not None and payload.college_id != target.college_id:
        if user.role.name != "super_admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only super_admin can reassign a user's college")
        if not db.get(College, payload.college_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "college_id does not exist")
        target.college_id = payload.college_id

    if payload.email is not None:
        target.email = payload.email
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.password is not None:
        target.password_hash = hash_password(payload.password)

    if payload.profile is not None:
        data = payload.profile.model_dump(exclude_unset=True)
        if target.profile is None:
            target.profile = Profile(name=data.get("name", target.username))
            db.add(target.profile)
        for field, value in data.items():
            setattr(target.profile, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Update violates a unique constraint")

    stmt = select(User).where(User.id == target.id).options(*_load_options())
    return _serialize(db.execute(stmt).scalar_one())


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    """Soft delete only: users are referenced across submissions, attempts,
    staff assignments etc. Deactivating also blocks login (see get_current_user)."""
    target = _get_managed_user_or_404(db, user_id, user)
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")
    target.is_active = False
    db.commit()
