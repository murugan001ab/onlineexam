from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.deps import AdminOrSuperAdmin, DbSession
from models.auth import Role, User
from models.college import College
from models.organization import Class, Department, StaffClass, StaffDepartment
from schemas.organization import (
    ClassCreate,
    ClassOut,
    ClassUpdate,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    StaffClassAssign,
    StaffClassOut,
    StaffClassUpdate,
    StaffDepartmentAssign,
    StaffDepartmentOut,
)

router = APIRouter(prefix="/admin", tags=["organization"])


def _scope_college_id(user: User, requested: Optional[int]) -> int:
    """super_admin must name a college_id; admin is always forced to their own."""
    if user.role.name == "super_admin":
        if requested is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "college_id is required")
        return requested
    return user.college_id


def _check_college_access(user: User, college_id: int) -> None:
    if user.role.name == "admin" and college_id != user.college_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this college")


# ------------------------------------------------------------- departments

def _get_department_or_404(db: DbSession, department_id: int, user: User) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")
    _check_college_access(user, department.college_id)
    return department


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: DbSession, user: User = AdminOrSuperAdmin, college_id: Optional[int] = None):
    stmt = select(Department)
    if user.role.name == "admin":
        stmt = stmt.where(Department.college_id == user.college_id)
    elif college_id is not None:
        stmt = stmt.where(Department.college_id == college_id)
    return db.execute(stmt.order_by(Department.name)).scalars().all()


@router.get("/departments/{department_id}", response_model=DepartmentOut)
def get_department(department_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    return _get_department_or_404(db, department_id, user)


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: DbSession, user: User = AdminOrSuperAdmin):
    college_id = _scope_college_id(user, payload.college_id)
    if not db.get(College, college_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "college_id does not exist")
    department = Department(college_id=college_id, name=payload.name, code=payload.code)
    db.add(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A department with this name already exists for this college")
    db.refresh(department)
    return department


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
def update_department(department_id: int, payload: DepartmentUpdate, db: DbSession, user: User = AdminOrSuperAdmin):
    department = _get_department_or_404(db, department_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(department, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A department with this name already exists for this college")
    db.refresh(department)
    return department


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    department = _get_department_or_404(db, department_id, user)
    db.delete(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Department still has classes or staff assignments — remove those first",
        )


# ------------------------------------------------------------------- classes

def _get_class_or_404(db: DbSession, class_id: int, user: User) -> Class:
    klass = db.get(Class, class_id)
    if klass is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found")
    _check_college_access(user, klass.college_id)
    return klass


@router.get("/classes", response_model=list[ClassOut])
def list_classes(
    db: DbSession,
    user: User = AdminOrSuperAdmin,
    department_id: Optional[int] = None,
    college_id: Optional[int] = None,
):
    stmt = select(Class)
    if user.role.name == "admin":
        stmt = stmt.where(Class.college_id == user.college_id)
    elif college_id is not None:
        stmt = stmt.where(Class.college_id == college_id)
    if department_id is not None:
        stmt = stmt.where(Class.department_id == department_id)
    return db.execute(stmt.order_by(Class.name)).scalars().all()


@router.get("/classes/{class_id}", response_model=ClassOut)
def get_class(class_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    return _get_class_or_404(db, class_id, user)


@router.post("/classes", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(payload: ClassCreate, db: DbSession, user: User = AdminOrSuperAdmin):
    department = db.get(Department, payload.department_id)
    if department is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "department_id does not exist")
    _check_college_access(user, department.college_id)

    klass = Class(
        college_id=department.college_id,
        department_id=department.id,
        name=payload.name,
        academic_year=payload.academic_year,
        section=payload.section,
    )
    db.add(klass)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A class with this name/section already exists in this department")
    db.refresh(klass)
    return klass


@router.patch("/classes/{class_id}", response_model=ClassOut)
def update_class(class_id: int, payload: ClassUpdate, db: DbSession, user: User = AdminOrSuperAdmin):
    klass = _get_class_or_404(db, class_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(klass, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A class with this name/section already exists in this department")
    db.refresh(klass)
    return klass


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    klass = _get_class_or_404(db, class_id, user)
    db.delete(klass)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Class still has enrolled students, staff assignments, or quiz targets — remove those first",
        )


# ------------------------------------------------------------ staff assignments

def _get_scoped_staff_or_404(db: DbSession, staff_id: int, user: User) -> User:
    stmt = select(User).join(Role).where(User.id == staff_id, Role.name == "staff")
    if user.role.name == "admin":
        stmt = stmt.where(User.college_id == user.college_id)
    staff = db.execute(stmt).scalar_one_or_none()
    if staff is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")
    return staff


@router.get("/staff/{staff_id}/departments", response_model=list[StaffDepartmentOut])
def list_staff_departments(staff_id: int, db: DbSession, user: User = AdminOrSuperAdmin, include_inactive: bool = False):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    stmt = select(StaffDepartment).where(StaffDepartment.user_id == staff.id)
    if not include_inactive:
        stmt = stmt.where(StaffDepartment.is_active.is_(True))
    rows = db.execute(stmt).scalars().all()
    return [
        StaffDepartmentOut(
            id=r.id,
            department_id=r.department_id,
            department_name=r.department.name,
            is_active=r.is_active,
            assigned_at=r.assigned_at,
        )
        for r in rows
    ]


@router.post("/staff/{staff_id}/departments", response_model=StaffDepartmentOut, status_code=status.HTTP_201_CREATED)
def assign_staff_department(staff_id: int, payload: StaffDepartmentAssign, db: DbSession, user: User = AdminOrSuperAdmin):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    department = _get_department_or_404(db, payload.department_id, user)
    if department.college_id != staff.college_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Department belongs to a different college than the staff member")

    existing = db.execute(
        select(StaffDepartment).where(
            StaffDepartment.user_id == staff.id, StaffDepartment.department_id == department.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.is_active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Staff is already assigned to this department")
        existing.is_active = True
        existing.assigned_at = datetime.now(timezone.utc)
        db.commit()
        row = existing
    else:
        row = StaffDepartment(
            user_id=staff.id,
            department_id=department.id,
            assigned_at=datetime.now(timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    return StaffDepartmentOut(
        id=row.id, department_id=row.department_id, department_name=department.name,
        is_active=row.is_active, assigned_at=row.assigned_at,
    )


@router.delete("/staff/{staff_id}/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_staff_department(staff_id: int, department_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    row = db.execute(
        select(StaffDepartment).where(
            StaffDepartment.user_id == staff.id, StaffDepartment.department_id == department_id
        )
    ).scalar_one_or_none()
    if row is None or not row.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    row.is_active = False
    db.commit()


@router.get("/staff/{staff_id}/classes", response_model=list[StaffClassOut])
def list_staff_classes(staff_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    rows = db.execute(select(StaffClass).where(StaffClass.staff_id == staff.id)).scalars().all()
    return [
        StaffClassOut(
            id=r.id, class_id=r.class_id, class_name=r.class_.name,
            is_incharge=r.is_incharge, assigned_at=r.assigned_at,
        )
        for r in rows
    ]


@router.post("/staff/{staff_id}/classes", response_model=StaffClassOut, status_code=status.HTTP_201_CREATED)
def assign_staff_class(staff_id: int, payload: StaffClassAssign, db: DbSession, user: User = AdminOrSuperAdmin):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    klass = _get_class_or_404(db, payload.class_id, user)
    if klass.college_id != staff.college_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Class belongs to a different college than the staff member")

    existing = db.execute(
        select(StaffClass).where(StaffClass.staff_id == staff.id, StaffClass.class_id == klass.id)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Staff is already assigned to this class")

    row = StaffClass(
        staff_id=staff.id,
        class_id=klass.id,
        is_incharge=payload.is_incharge,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return StaffClassOut(id=row.id, class_id=row.class_id, class_name=klass.name, is_incharge=row.is_incharge, assigned_at=row.assigned_at)


@router.patch("/staff/{staff_id}/classes/{class_id}", response_model=StaffClassOut)
def update_staff_class(staff_id: int, class_id: int, payload: StaffClassUpdate, db: DbSession, user: User = AdminOrSuperAdmin):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    row = db.execute(
        select(StaffClass).where(StaffClass.staff_id == staff.id, StaffClass.class_id == class_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    row.is_incharge = payload.is_incharge
    db.commit()
    db.refresh(row)
    return StaffClassOut(id=row.id, class_id=row.class_id, class_name=row.class_.name, is_incharge=row.is_incharge, assigned_at=row.assigned_at)


@router.delete("/staff/{staff_id}/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_staff_class(staff_id: int, class_id: int, db: DbSession, user: User = AdminOrSuperAdmin):
    staff = _get_scoped_staff_or_404(db, staff_id, user)
    row = db.execute(
        select(StaffClass).where(StaffClass.staff_id == staff.id, StaffClass.class_id == class_id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    db.delete(row)
    db.commit()
