from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.auth import User
from models.problem import Problem
from models.student import Student
from models.training import TrainingAssignment, TrainingAttempt, TrainingSubmission
from schemas.training import (
    PromptSubmit,
    TrainingAssignmentCreate,
    TrainingAssignmentOut,
    TrainingAssignmentUpdate,
    TrainingAttemptOut,
    TrainingSubmissionCreate,
    TrainingSubmissionOut,
)
from utils.llm import generate_code_from_prompt, is_configured as llm_is_configured
from utils.training_runner import grade_training_submission

admin_router = APIRouter(prefix="/admin/training-assignments", tags=["training"])
student_router = APIRouter(prefix="/training", tags=["training"])

RequireStudent = Depends(require_roles("student"))


def _get_student_or_404(db: DbSession, user: User) -> Student:
    student = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return student


def _serialize_assignment(a: TrainingAssignment) -> TrainingAssignmentOut:
    return TrainingAssignmentOut(
        id=a.id,
        college_id=a.college_id,
        problem_id=a.problem_id,
        problem_title=a.problem.title if a.problem else None,
        title=a.title,
        instructions=a.instructions,
        max_debug_submissions=a.max_debug_submissions,
        time_limit_minutes=a.time_limit_minutes,
        created_by=a.created_by,
        created_at=a.created_at,
    )


def _serialize_attempt(attempt: TrainingAttempt) -> TrainingAttemptOut:
    return TrainingAttemptOut(
        id=attempt.id,
        assignment_id=attempt.assignment_id,
        student_id=attempt.student_id,
        status=attempt.status,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        prompt=attempt.prompt,
        prompt_submitted_at=attempt.prompt_submitted_at,
        generated_code=attempt.generated_code,
        generation_model=attempt.generation_model,
        test_pass_rate=attempt.test_pass_rate,
        debug_submission_count=attempt.debug_submission_count,
        max_debug_submissions=attempt.assignment.max_debug_submissions if attempt.assignment else None,
        final_score=attempt.final_score,
    )


def _expire_if_overdue(db: DbSession, attempt: TrainingAttempt) -> None:
    assignment = attempt.assignment
    if (
        attempt.status in ("completed", "expired")
        or assignment.time_limit_minutes is None
        or attempt.started_at is None
    ):
        return
    deadline = attempt.started_at + timedelta(minutes=assignment.time_limit_minutes)
    if datetime.now(timezone.utc) > deadline:
        attempt.status = "expired"
        attempt.completed_at = datetime.now(timezone.utc)
        db.commit()


# ==================================================================
# Admin/staff: assignment CRUD + attempt oversight
# ==================================================================

def _get_assignment_or_404(db: DbSession, assignment_id: int, college_id: int) -> TrainingAssignment:
    a = db.execute(
        select(TrainingAssignment)
        .where(TrainingAssignment.id == assignment_id, TrainingAssignment.college_id == college_id)
        .options(selectinload(TrainingAssignment.problem))
    ).scalar_one_or_none()
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Training assignment not found")
    return a


@admin_router.get("", response_model=list[TrainingAssignmentOut])
def list_assignments(db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    rows = db.execute(
        select(TrainingAssignment)
        .where(TrainingAssignment.college_id == user.college_id)
        .options(selectinload(TrainingAssignment.problem))
        .order_by(TrainingAssignment.id.desc())
    ).scalars().all()
    return [_serialize_assignment(a) for a in rows]


@admin_router.get("/{assignment_id}", response_model=TrainingAssignmentOut)
def get_assignment(assignment_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    return _serialize_assignment(_get_assignment_or_404(db, assignment_id, user.college_id))


@admin_router.post("", response_model=TrainingAssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: TrainingAssignmentCreate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    problem = db.execute(
        select(Problem).where(Problem.id == payload.problem_id, Problem.college_id == user.college_id)
    ).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "problem_id does not exist for this college")

    assignment = TrainingAssignment(college_id=user.college_id, created_by=user.id, **payload.model_dump())
    db.add(assignment)
    db.commit()
    return _serialize_assignment(_get_assignment_or_404(db, assignment.id, user.college_id))


@admin_router.patch("/{assignment_id}", response_model=TrainingAssignmentOut)
def update_assignment(
    assignment_id: int,
    payload: TrainingAssignmentUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    assignment = _get_assignment_or_404(db, assignment_id, user.college_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)
    db.commit()
    return _serialize_assignment(_get_assignment_or_404(db, assignment.id, user.college_id))


@admin_router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    assignment = _get_assignment_or_404(db, assignment_id, user.college_id)
    db.delete(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Assignment still has student attempts — remove those first")


@admin_router.get("/{assignment_id}/attempts", response_model=list[TrainingAttemptOut])
def list_assignment_attempts(
    assignment_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    status_: Optional[str] = None,
):
    assignment = _get_assignment_or_404(db, assignment_id, user.college_id)
    stmt = (
        select(TrainingAttempt)
        .where(TrainingAttempt.assignment_id == assignment.id)
        .options(selectinload(TrainingAttempt.assignment))
    )
    if status_ is not None:
        stmt = stmt.where(TrainingAttempt.status == status_)
    rows = db.execute(stmt.order_by(TrainingAttempt.id.desc())).scalars().all()
    return [_serialize_attempt(a) for a in rows]


# ==================================================================
# Student-facing: browse assignments, run the attempt flow
# ==================================================================

@student_router.get("/assignments", response_model=list[TrainingAssignmentOut])
def list_my_available_assignments(db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    rows = db.execute(
        select(TrainingAssignment)
        .where(TrainingAssignment.college_id == student.college_id)
        .options(selectinload(TrainingAssignment.problem))
        .order_by(TrainingAssignment.id.desc())
    ).scalars().all()
    return [_serialize_assignment(a) for a in rows]


def _get_own_attempt_or_404(db: DbSession, attempt_id: int, student: Student) -> TrainingAttempt:
    attempt = db.execute(
        select(TrainingAttempt)
        .where(TrainingAttempt.id == attempt_id, TrainingAttempt.student_id == student.id)
        .options(selectinload(TrainingAttempt.assignment).selectinload(TrainingAssignment.problem))
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    return attempt


@student_router.post(
    "/assignments/{assignment_id}/attempts/start",
    response_model=TrainingAttemptOut,
    status_code=status.HTTP_201_CREATED,
)
def start_attempt(assignment_id: int, db: DbSession, user: User = RequireStudent):
    """Idempotent: returns the existing attempt if the student already started one,
    rather than restarting their timer."""
    student = _get_student_or_404(db, user)
    assignment = db.execute(
        select(TrainingAssignment)
        .where(TrainingAssignment.id == assignment_id, TrainingAssignment.college_id == student.college_id)
        .options(selectinload(TrainingAssignment.problem))
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Training assignment not found")

    existing = db.execute(
        select(TrainingAttempt).where(
            TrainingAttempt.assignment_id == assignment.id, TrainingAttempt.student_id == student.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.assignment = assignment
        _expire_if_overdue(db, existing)
        return _serialize_attempt(existing)

    attempt = TrainingAttempt(
        assignment_id=assignment.id,
        student_id=student.id,
        started_at=datetime.now(timezone.utc),
        status="not_started",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    attempt.assignment = assignment
    return _serialize_attempt(attempt)


@student_router.get("/attempts", response_model=list[TrainingAttemptOut])
def list_my_attempts(db: DbSession, user: User = RequireStudent, assignment_id: Optional[int] = None):
    student = _get_student_or_404(db, user)
    stmt = (
        select(TrainingAttempt)
        .where(TrainingAttempt.student_id == student.id)
        .options(selectinload(TrainingAttempt.assignment))
    )
    if assignment_id is not None:
        stmt = stmt.where(TrainingAttempt.assignment_id == assignment_id)
    rows = db.execute(stmt.order_by(TrainingAttempt.id.desc())).scalars().all()
    return [_serialize_attempt(a) for a in rows]


@student_router.get("/attempts/{attempt_id}", response_model=TrainingAttemptOut)
def get_my_attempt(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    return _serialize_attempt(attempt)


@student_router.post("/attempts/{attempt_id}/prompt", response_model=TrainingAttemptOut)
async def submit_prompt(attempt_id: int, payload: PromptSubmit, db: DbSession, user: User = RequireStudent):
    """One-shot: once prompt_submitted_at is set, this can never be called again for
    this attempt — that's the server-side lock, independent of client state."""
    if not llm_is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Code generation is not configured on this server (ANTHROPIC_API_KEY missing)",
        )

    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status == "expired":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt's time limit has expired")
    if attempt.prompt_submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A prompt has already been submitted for this attempt")

    problem = attempt.assignment.problem
    try:
        generation = await generate_code_from_prompt(
            problem_title=problem.title,
            problem_description=problem.description or "",
            constraints=problem.constraints,
            language=payload.language,
            student_prompt=payload.prompt,
        )
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Code generation failed — try again")

    now = datetime.now(timezone.utc)
    attempt.prompt = payload.prompt
    attempt.prompt_submitted_at = now
    attempt.generated_code = generation["code"]
    attempt.generation_model = generation["model"]
    attempt.generation_input_tokens = generation.get("input_tokens")
    attempt.generation_output_tokens = generation.get("output_tokens")
    attempt.status = "debugging"
    db.commit()
    db.refresh(attempt)
    return _serialize_attempt(attempt)


@student_router.post(
    "/attempts/{attempt_id}/submissions",
    response_model=TrainingSubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_debug_code(
    attempt_id: int,
    payload: TrainingSubmissionCreate,
    db: DbSession,
    background_tasks: BackgroundTasks,
    user: User = RequireStudent,
):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)

    if attempt.status == "expired":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt's time limit has expired")
    if attempt.status == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is already completed")
    if attempt.prompt_submitted_at is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Submit a prompt before debugging")

    max_debug = attempt.assignment.max_debug_submissions
    if max_debug is not None and attempt.debug_submission_count >= max_debug:
        raise HTTPException(status.HTTP_409_CONFLICT, "No debug submissions remaining for this attempt")

    submission = TrainingSubmission(
        training_attempt_id=attempt.id,
        code=payload.code,
        language=payload.language,
        status="queued",
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(submission)
    attempt.debug_submission_count += 1
    db.commit()
    db.refresh(submission)
    background_tasks.add_task(grade_training_submission, submission.id)
    return submission


@student_router.get("/attempts/{attempt_id}/submissions", response_model=list[TrainingSubmissionOut])
def list_my_debug_submissions(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    rows = db.execute(
        select(TrainingSubmission)
        .where(TrainingSubmission.training_attempt_id == attempt.id)
        .order_by(TrainingSubmission.id.desc())
    ).scalars().all()
    return rows
