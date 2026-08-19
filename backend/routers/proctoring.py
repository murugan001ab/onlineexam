import base64
import binascii
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.attempt import ExamAttempt
from models.auth import User
from models.exam import Exam
from models.proctoring import ProctoringEvent, ProctoringSnapshot
from models.student import Student
from schemas.proctoring import (
    ProctoringEventBatchIn,
    ProctoringEventBatchOut,
    ProctoringEventOut,
    ProctoringSnapshotIn,
    ProctoringSnapshotOut,
    ProctoringSummaryOut,
)
from utils.storage import file_url, save_bytes

student_router = APIRouter(prefix="/exam-attempts", tags=["proctoring"])
admin_router = APIRouter(prefix="/admin", tags=["proctoring"])

RequireStudent = Depends(require_roles("student"))

# Events that count against Exam.max_tab_switch_warnings. Everything else
# (face_missing/multiple_faces/copy/paste/right_click/devtools) is logged
# for admin review but doesn't by itself auto-disqualify — those need a
# human look rather than a hard cutoff.
_WARNING_EVENT_TYPES = {"tab_switch", "window_blur", "fullscreen_exit"}


def _get_student_or_404(db: DbSession, user: User) -> Student:
    student = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return student


def _get_own_attempt_or_404(db: DbSession, attempt_id: int, student: Student) -> ExamAttempt:
    attempt = db.execute(
        select(ExamAttempt)
        .where(ExamAttempt.id == attempt_id, ExamAttempt.student_id == student.id)
        .options(selectinload(ExamAttempt.exam))
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    return attempt


# ==================================================================
# Student-facing: called from the exam-taking page while in progress
# ==================================================================

@student_router.post(
    "/{attempt_id}/proctoring/events",
    response_model=ProctoringEventBatchOut,
)
def submit_proctoring_events(
    attempt_id: int, payload: ProctoringEventBatchIn, db: DbSession, user: User = RequireStudent
):
    """Buffered event flush from the exam-taking page. If the running total
    of warning-eligible events (tab switch / window blur / fullscreen exit)
    exceeds the exam's max_tab_switch_warnings, the attempt is immediately
    flipped to 'disqualified' and the response tells the frontend to lock
    the exam and show why."""
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    if attempt.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not in progress")

    now = datetime.now(timezone.utc)
    for e in payload.events:
        db.add(
            ProctoringEvent(
                attempt_id=attempt.id,
                event_type=e.event_type,
                metadata_=e.metadata,
                occurred_at=e.occurred_at or now,
            )
        )
    db.flush()

    warning_count = db.execute(
        select(func.count(ProctoringEvent.id)).where(
            ProctoringEvent.attempt_id == attempt.id,
            ProctoringEvent.event_type.in_(_WARNING_EVENT_TYPES),
        )
    ).scalar_one()

    max_warnings = attempt.exam.max_tab_switch_warnings if attempt.exam else 3
    disqualified = False
    if attempt.exam and attempt.exam.proctoring_enabled and warning_count > max_warnings:
        attempt.status = "disqualified"
        attempt.submitted_at = now
        disqualified = True

    db.commit()
    return ProctoringEventBatchOut(
        accepted=len(payload.events),
        warning_count=warning_count,
        max_warnings=max_warnings,
        disqualified=disqualified,
    )


@student_router.post("/{attempt_id}/proctoring/snapshot", response_model=ProctoringSnapshotOut)
def submit_proctoring_snapshot(attempt_id: int, payload: ProctoringSnapshotIn, db: DbSession, user: User = RequireStudent):
    """Accepts a periodic webcam snapshot as a base64 data URL
    ("data:image/jpeg;base64,...." or bare base64) captured client-side by
    the exam page. face_count/flagged are left null here — wire in a
    face-detection pass (e.g. face-api.js client-side, or a server model)
    to populate them; the column is already in place."""
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    if attempt.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not in progress")

    raw = payload.image_base64.split(",", 1)[-1]
    try:
        data = base64.b64decode(raw)
    except (binascii.Error, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "image_base64 is not valid base64")

    relative_path = save_bytes(data, subdir=f"proctoring/{attempt.id}", content_type="image/jpeg")
    snapshot = ProctoringSnapshot(
        attempt_id=attempt.id,
        storage_key=relative_path,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return ProctoringSnapshotOut(
        id=snapshot.id,
        file_url=file_url(snapshot.storage_key),
        face_count=snapshot.face_count,
        flagged=snapshot.flagged,
        captured_at=snapshot.captured_at,
    )


# ==================================================================
# Admin/staff: review proctoring history for an attempt
# ==================================================================

@admin_router.get(
    "/exams/{exam_id}/attempts/{attempt_id}/proctoring",
    response_model=ProctoringSummaryOut,
)
def review_attempt_proctoring(
    exam_id: int, attempt_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))
):
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    attempt = db.execute(
        select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.exam_id == exam.id)
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")

    events = db.execute(
        select(ProctoringEvent).where(ProctoringEvent.attempt_id == attempt.id).order_by(ProctoringEvent.occurred_at)
    ).scalars().all()
    snapshots = db.execute(
        select(ProctoringSnapshot)
        .where(ProctoringSnapshot.attempt_id == attempt.id)
        .order_by(ProctoringSnapshot.captured_at)
    ).scalars().all()

    counts: dict[str, int] = {}
    for e in events:
        key = e.event_type or "unknown"
        counts[key] = counts.get(key, 0) + 1

    return ProctoringSummaryOut(
        attempt_id=attempt.id,
        total_events=len(events),
        event_counts=counts,
        flagged_snapshot_count=sum(1 for s in snapshots if s.flagged),
        disqualified=attempt.status == "disqualified",
        events=[ProctoringEventOut(id=e.id, event_type=e.event_type, metadata=e.metadata_, occurred_at=e.occurred_at) for e in events],
        snapshots=[
            ProctoringSnapshotOut(
                id=s.id, file_url=file_url(s.storage_key), face_count=s.face_count,
                flagged=s.flagged, captured_at=s.captured_at,
            )
            for s in snapshots
        ],
    )
