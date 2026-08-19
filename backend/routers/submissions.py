import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, CurrentUser, DbSession, require_roles
from models.auth import User
from models.problem import Problem, Submission
from schemas.problem import SubmissionAdminOut, SubmissionCreate, SubmissionOut
from utils.code_runner import grade_submission

router = APIRouter(prefix="/submissions", tags=["submissions"])
admin_router = APIRouter(prefix="/admin/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    db: DbSession,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    problem = db.get(Problem, payload.problem_id)
    if problem is None or problem.college_id != user.college_id or not problem.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")

    submission = Submission(
        uuid=str(uuid_lib.uuid4()),
        college_id=user.college_id,
        user_id=user.id,
        problem_id=problem.id,
        language=payload.language,
        code=payload.code,
        status="queued",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    background_tasks.add_task(grade_submission, submission.id)
    return submission


@router.get("", response_model=list[SubmissionOut])
def list_my_submissions(
    db: DbSession,
    user: CurrentUser,
    problem_id: Optional[int] = None,
):
    stmt = select(Submission).where(Submission.user_id == user.id)
    if problem_id:
        stmt = stmt.where(Submission.problem_id == problem_id)
    return db.execute(stmt.order_by(Submission.id.desc())).scalars().all()


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: DbSession, user: CurrentUser):
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    is_staff = user.role.name in STAFF_ROLES
    if submission.user_id != user.id and not is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your submission")
    return submission


# --------------------------------------------------------- staff/admin review

@admin_router.get("", response_model=list[SubmissionAdminOut])
def list_college_submissions(
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    problem_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status_: Optional[str] = None,
):
    """All submissions for the caller's college, for staff/admin to review."""
    stmt = (
        select(Submission)
        .where(Submission.college_id == user.college_id)
        .options(selectinload(Submission.problem))
        .order_by(Submission.id.desc())
    )
    if problem_id is not None:
        stmt = stmt.where(Submission.problem_id == problem_id)
    if student_id is not None:
        stmt = stmt.where(Submission.user_id == student_id)
    if status_ is not None:
        stmt = stmt.where(Submission.status == status_)

    submissions = db.execute(stmt).scalars().all()
    if not submissions:
        return []

    student_ids = {s.user_id for s in submissions}
    students = db.execute(
        select(User).where(User.id.in_(student_ids))
    ).scalars().all()
    username_by_id = {u.id: u.username for u in students}

    return [
        SubmissionAdminOut.from_submission(
            s,
            student_username=username_by_id.get(s.user_id),
            problem_title=s.problem.title if s.problem else None,
        )
        for s in submissions
    ]
