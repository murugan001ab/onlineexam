import re
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from core.settings import Settings
from models.auth import User
from models.catalog import ExamType, Topic
from models.entrance import ExamRegistration, ExamSlot, SlotHold
from models.exam import Exam, ExamProblem, ExamQuiz, ExamTopicWeight
from models.problem import Problem
from models.question import Question
from models.quiz import Quiz
from schemas.exam import (
    ExamCreate,
    ExamOut,
    ExamProblemAssign,
    ExamProblemOut,
    ExamProblemUpdate,
    ExamQuizAssign,
    ExamQuizOut,
    ExamQuizUpdate,
    ExamSlotCreate,
    ExamSlotOut,
    ExamSlotUpdate,
    ExamTopicWeightCreate,
    ExamTopicWeightOut,
    ExamTopicWeightUpdate,
    ExamTypeCreate,
    ExamTypeOut,
    ExamTypeUpdate,
    ExamUpdate,
)

router = APIRouter(prefix="/admin", tags=["entrance-exam"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _generate_public_slug(db: DbSession, name: str) -> str:
    base = _SLUG_RE.sub("-", name.lower()).strip("-")[:40] or "exam"
    while True:
        candidate = f"{base}-{secrets.token_hex(3)}"
        if db.execute(select(Exam).where(Exam.public_slug == candidate)).scalar_one_or_none() is None:
            return candidate

_ACTIVE_REGISTRATION_STATUSES = ("pending_payment", "confirmed", "completed")


# --------------------------------------------------------------- exam types
# Global lookup (not college-scoped) — restricted to super_admin since it
# affects every college's exam catalog.

def _get_exam_type_or_404(db: DbSession, exam_type_id: int) -> ExamType:
    exam_type = db.get(ExamType, exam_type_id)
    if exam_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam type not found")
    return exam_type


@router.get("/exam-types", response_model=list[ExamTypeOut])
def list_exam_types(db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    return db.execute(select(ExamType).order_by(ExamType.name)).scalars().all()


@router.post("/exam-types", response_model=ExamTypeOut, status_code=status.HTTP_201_CREATED)
def create_exam_type(
    payload: ExamTypeCreate,
    db: DbSession,
    user: User = Depends(require_roles("super_admin")),
):
    exam_type = ExamType(**payload.model_dump())
    db.add(exam_type)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An exam type with this name already exists")
    db.refresh(exam_type)
    return exam_type


@router.patch("/exam-types/{exam_type_id}", response_model=ExamTypeOut)
def update_exam_type(
    exam_type_id: int,
    payload: ExamTypeUpdate,
    db: DbSession,
    user: User = Depends(require_roles("super_admin")),
):
    exam_type = _get_exam_type_or_404(db, exam_type_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exam_type, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An exam type with this name already exists")
    db.refresh(exam_type)
    return exam_type


@router.delete("/exam-types/{exam_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam_type(
    exam_type_id: int,
    db: DbSession,
    user: User = Depends(require_roles("super_admin")),
):
    exam_type = _get_exam_type_or_404(db, exam_type_id)
    db.delete(exam_type)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Exam type still has exams using it — remove those first")


# --------------------------------------------------------------------- exams

def _get_exam_or_404(db: DbSession, exam_id: int, college_id: int) -> Exam:
    exam = db.execute(
        select(Exam).where(Exam.id == exam_id, Exam.college_id == college_id).options(selectinload(Exam.exam_type))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    return exam


def _serialize_exam(db: DbSession, exam: Exam) -> ExamOut:
    registration_count = db.execute(
        select(func.count(ExamRegistration.id)).where(
            ExamRegistration.exam_id == exam.id,
            ExamRegistration.status.in_(_ACTIVE_REGISTRATION_STATUSES),
        )
    ).scalar_one()
    slot_count = db.execute(
        select(func.count(ExamSlot.id)).where(
            ExamSlot.exam_id == exam.id, ExamSlot.status != "cancelled"
        )
    ).scalar_one()
    return ExamOut(
        id=exam.id,
        college_id=exam.college_id,
        name=exam.name,
        description=exam.description,
        exam_type_id=exam.exam_type_id,
        exam_type_name=exam.exam_type.name if exam.exam_type else None,
        starts_at=exam.starts_at,
        ends_at=exam.ends_at,
        duration_minutes=exam.duration_minutes,
        fee=exam.fee,
        fee_currency=exam.fee_currency,
        status=exam.status,
        public_slug=exam.public_slug,
        public_url=f"{Settings.FRONTEND_URL.rstrip('/')}/e/{exam.public_slug}" if exam.public_slug else None,
        proctoring_enabled=exam.proctoring_enabled,
        fullscreen_required=exam.fullscreen_required,
        camera_required=exam.camera_required,
        max_tab_switch_warnings=exam.max_tab_switch_warnings,
        registration_count=registration_count,
        slot_count=slot_count,
        created_by=exam.created_by,
        created_at=exam.created_at,
    )


@router.get("/exams", response_model=list[ExamOut])
def list_exams(
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    exam_type_id: Optional[int] = None,
    status_: Optional[str] = None,
):
    stmt = select(Exam).where(Exam.college_id == user.college_id).options(selectinload(Exam.exam_type))
    if exam_type_id is not None:
        stmt = stmt.where(Exam.exam_type_id == exam_type_id)
    if status_ is not None:
        stmt = stmt.where(Exam.status == status_)
    exams = db.execute(stmt.order_by(Exam.id.desc())).scalars().all()
    return [_serialize_exam(db, e) for e in exams]


@router.get("/exams/{exam_id}", response_model=ExamOut)
def get_exam(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    return _serialize_exam(db, _get_exam_or_404(db, exam_id, user.college_id))


@router.post("/exams", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    if not db.get(ExamType, payload.exam_type_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "exam_type_id does not exist")
    exam = Exam(
        college_id=user.college_id,
        created_by=user.id,
        public_slug=_generate_public_slug(db, payload.name),
        **payload.model_dump(),
    )
    db.add(exam)
    db.commit()
    return _serialize_exam(db, _get_exam_or_404(db, exam.id, user.college_id))


@router.patch("/exams/{exam_id}", response_model=ExamOut)
def update_exam(
    exam_id: int,
    payload: ExamUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    data = payload.model_dump(exclude_unset=True)
    if "exam_type_id" in data and data["exam_type_id"] is not None:
        if not db.get(ExamType, data["exam_type_id"]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "exam_type_id does not exist")
    new_starts = data.get("starts_at", exam.starts_at)
    new_ends = data.get("ends_at", exam.ends_at)
    if new_starts and new_ends and new_ends <= new_starts:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ends_at must be after starts_at")
    for field, value in data.items():
        setattr(exam, field, value)
    db.commit()
    return _serialize_exam(db, _get_exam_or_404(db, exam.id, user.college_id))


@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    db.delete(exam)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Exam still has registrations, quizzes, or attempts linked — remove those first",
        )


# ---------------------------------------------------------------- exam quiz

@router.get("/exams/{exam_id}/quizzes", response_model=list[ExamQuizOut])
def list_exam_quizzes(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    rows = db.execute(
        select(ExamQuiz)
        .where(ExamQuiz.exam_id == exam.id)
        .options(selectinload(ExamQuiz.quiz))
        .order_by(ExamQuiz.order_index)
    ).scalars().all()
    return [
        ExamQuizOut(id=r.id, quiz_id=r.quiz_id, quiz_name=r.quiz.name, order_index=r.order_index, weight=r.weight)
        for r in rows
    ]


@router.post("/exams/{exam_id}/quizzes", response_model=ExamQuizOut, status_code=status.HTTP_201_CREATED)
def assign_exam_quiz(
    exam_id: int,
    payload: ExamQuizAssign,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    quiz = db.execute(
        select(Quiz).where(Quiz.id == payload.quiz_id, Quiz.college_id == user.college_id)
    ).scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "quiz_id does not exist for this college")

    row = ExamQuiz(exam_id=exam.id, quiz_id=quiz.id, order_index=payload.order_index, weight=payload.weight)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz is already linked to the exam")
    db.refresh(row)
    return ExamQuizOut(id=row.id, quiz_id=row.quiz_id, quiz_name=quiz.name, order_index=row.order_index, weight=row.weight)


@router.patch("/exams/{exam_id}/quizzes/{exam_quiz_id}", response_model=ExamQuizOut)
def update_exam_quiz(
    exam_id: int,
    exam_quiz_id: int,
    payload: ExamQuizUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    row = db.execute(
        select(ExamQuiz)
        .where(ExamQuiz.id == exam_quiz_id, ExamQuiz.exam_id == exam.id)
        .options(selectinload(ExamQuiz.quiz))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam-quiz link not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ExamQuizOut(id=row.id, quiz_id=row.quiz_id, quiz_name=row.quiz.name, order_index=row.order_index, weight=row.weight)


@router.delete("/exams/{exam_id}/quizzes/{exam_quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_exam_quiz(
    exam_id: int,
    exam_quiz_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    row = db.execute(
        select(ExamQuiz).where(ExamQuiz.id == exam_quiz_id, ExamQuiz.exam_id == exam.id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam-quiz link not found")
    db.delete(row)
    db.commit()


# ------------------------------------------------------------- exam problem

@router.get("/exams/{exam_id}/problems", response_model=list[ExamProblemOut])
def list_exam_problems(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    rows = db.execute(
        select(ExamProblem)
        .where(ExamProblem.exam_id == exam.id)
        .options(selectinload(ExamProblem.problem))
        .order_by(ExamProblem.order_index)
    ).scalars().all()
    return [
        ExamProblemOut(id=r.id, problem_id=r.problem_id, problem_title=r.problem.title, order_index=r.order_index, marks=r.marks)
        for r in rows
    ]


@router.post("/exams/{exam_id}/problems", response_model=ExamProblemOut, status_code=status.HTTP_201_CREATED)
def assign_exam_problem(
    exam_id: int,
    payload: ExamProblemAssign,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    problem = db.execute(
        select(Problem).where(Problem.id == payload.problem_id, Problem.college_id == user.college_id)
    ).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "problem_id does not exist for this college")

    row = ExamProblem(exam_id=exam.id, problem_id=problem.id, order_index=payload.order_index, marks=payload.marks)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This problem is already linked to the exam")
    db.refresh(row)
    return ExamProblemOut(id=row.id, problem_id=row.problem_id, problem_title=problem.title, order_index=row.order_index, marks=row.marks)


@router.patch("/exams/{exam_id}/problems/{exam_problem_id}", response_model=ExamProblemOut)
def update_exam_problem(
    exam_id: int,
    exam_problem_id: int,
    payload: ExamProblemUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    row = db.execute(
        select(ExamProblem)
        .where(ExamProblem.id == exam_problem_id, ExamProblem.exam_id == exam.id)
        .options(selectinload(ExamProblem.problem))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam-problem link not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ExamProblemOut(id=row.id, problem_id=row.problem_id, problem_title=row.problem.title, order_index=row.order_index, marks=row.marks)


@router.delete("/exams/{exam_id}/problems/{exam_problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_exam_problem(
    exam_id: int,
    exam_problem_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    row = db.execute(
        select(ExamProblem).where(ExamProblem.id == exam_problem_id, ExamProblem.exam_id == exam.id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam-problem link not found")
    db.delete(row)
    db.commit()


# --------------------------------------------------------- exam topic weight

def _active_question_count(db: DbSession, college_id: int, topic_id: int) -> int:
    return db.execute(
        select(func.count(Question.id)).where(
            Question.college_id == college_id,
            Question.topic_id == topic_id,
            Question.is_active.is_(True),
        )
    ).scalar_one()


@router.get("/exams/{exam_id}/topic-weights", response_model=list[ExamTopicWeightOut])
def list_topic_weights(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    rows = db.execute(
        select(ExamTopicWeight)
        .where(ExamTopicWeight.exam_id == exam.id)
        .options(selectinload(ExamTopicWeight.topic))
    ).scalars().all()
    return [
        ExamTopicWeightOut(
            id=r.id, topic_id=r.topic_id, topic_name=r.topic.name,
            question_count=r.question_count, weight=r.weight,
        )
        for r in rows
    ]


@router.post("/exams/{exam_id}/topic-weights", response_model=ExamTopicWeightOut, status_code=status.HTTP_201_CREATED)
def add_topic_weight(
    exam_id: int,
    payload: ExamTopicWeightCreate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    topic = db.execute(
        select(Topic).where(Topic.id == payload.topic_id, Topic.college_id == user.college_id)
    ).scalar_one_or_none()
    if topic is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "topic_id does not exist for this college")

    available = _active_question_count(db, user.college_id, topic.id)
    if payload.question_count > available:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{topic.name} only has {available} active question(s) — reduce question_count or add more questions to this topic first",
        )

    row = ExamTopicWeight(
        exam_id=exam.id, topic_id=topic.id, question_count=payload.question_count, weight=payload.weight
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This topic already has a weight configured for the exam")
    db.refresh(row)
    return ExamTopicWeightOut(
        id=row.id, topic_id=row.topic_id, topic_name=topic.name,
        question_count=row.question_count, weight=row.weight,
    )


@router.patch("/exams/{exam_id}/topic-weights/{weight_id}", response_model=ExamTopicWeightOut)
def update_topic_weight(
    exam_id: int,
    weight_id: int,
    payload: ExamTopicWeightUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    row = db.execute(
        select(ExamTopicWeight)
        .where(ExamTopicWeight.id == weight_id, ExamTopicWeight.exam_id == exam.id)
        .options(selectinload(ExamTopicWeight.topic))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic weight not found")
    data = payload.model_dump(exclude_unset=True)
    if "question_count" in data:
        available = _active_question_count(db, user.college_id, row.topic_id)
        if data["question_count"] > available:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"{row.topic.name} only has {available} active question(s) — reduce question_count or add more questions to this topic first",
            )
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ExamTopicWeightOut(
        id=row.id, topic_id=row.topic_id, topic_name=row.topic.name,
        question_count=row.question_count, weight=row.weight,
    )


@router.delete("/exams/{exam_id}/topic-weights/{weight_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_topic_weight(
    exam_id: int,
    weight_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = _get_exam_or_404(db, exam_id, user.college_id)
    row = db.execute(
        select(ExamTopicWeight).where(ExamTopicWeight.id == weight_id, ExamTopicWeight.exam_id == exam.id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic weight not found")
    db.delete(row)
    db.commit()


# ------------------------------------------------------------------ slots

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


def _get_slot_or_404(db: DbSession, slot_id: int, college_id: int) -> ExamSlot:
    slot = db.execute(
        select(ExamSlot).where(ExamSlot.id == slot_id, ExamSlot.college_id == college_id)
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam slot not found")
    return slot


@router.get("/exam-slots", response_model=list[ExamSlotOut])
def list_exam_slots(
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    exam_id: Optional[int] = None,
    status_: Optional[str] = None,
):
    stmt = select(ExamSlot).where(ExamSlot.college_id == user.college_id)
    if exam_id is not None:
        stmt = stmt.where(ExamSlot.exam_id == exam_id)
    if status_ is not None:
        stmt = stmt.where(ExamSlot.status == status_)
    slots = db.execute(stmt.order_by(ExamSlot.starts_at)).scalars().all()
    return [_serialize_slot(db, s) for s in slots]


@router.get("/exam-slots/{slot_id}", response_model=ExamSlotOut)
def get_exam_slot(slot_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    return _serialize_slot(db, _get_slot_or_404(db, slot_id, user.college_id))


@router.post("/exam-slots", response_model=ExamSlotOut, status_code=status.HTTP_201_CREATED)
def create_exam_slot(payload: ExamSlotCreate, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ends_at must be after starts_at")
    _get_exam_or_404(db, payload.exam_id, user.college_id)
    slot = ExamSlot(college_id=user.college_id, **payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _serialize_slot(db, slot)


@router.patch("/exam-slots/{slot_id}", response_model=ExamSlotOut)
def update_exam_slot(
    slot_id: int,
    payload: ExamSlotUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    slot = _get_slot_or_404(db, slot_id, user.college_id)
    data = payload.model_dump(exclude_unset=True)
    new_starts = data.get("starts_at", slot.starts_at)
    new_ends = data.get("ends_at", slot.ends_at)
    if new_ends <= new_starts:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ends_at must be after starts_at")
    if "max_capacity" in data:
        booked = _slot_booked_count(db, slot.id)
        if data["max_capacity"] < booked:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot set capacity below current bookings ({booked})",
            )
    for field, value in data.items():
        setattr(slot, field, value)
    db.commit()
    db.refresh(slot)
    return _serialize_slot(db, slot)


@router.delete("/exam-slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_exam_slot(slot_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    """Soft delete: slots are referenced by registrations/holds, so this just
    marks the slot cancelled rather than deleting the row."""
    slot = _get_slot_or_404(db, slot_id, user.college_id)
    slot.status = "cancelled"
    db.commit()
