from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.auth import User
from models.organization import Class
from models.question import Question, QuizQuestion
from models.quiz import Quiz, QuizClassTarget
from schemas.quiz import (
    QuizClassTargetAssign,
    QuizClassTargetOut,
    QuizCreate,
    QuizOut,
    QuizQuestionAdd,
    QuizQuestionOut,
    QuizQuestionReorder,
    QuizUpdate,
)

router = APIRouter(prefix="/admin/quizzes", tags=["quizzes"])


def _get_quiz_or_404(db: DbSession, quiz_id: int, college_id: int) -> Quiz:
    quiz = db.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.college_id == college_id)
    ).scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    return quiz


def _serialize(quiz: Quiz, question_count: int = 0) -> QuizOut:
    return QuizOut(
        id=quiz.id,
        college_id=quiz.college_id,
        name=quiz.name,
        description=quiz.description,
        quiz_type=quiz.quiz_type,
        subject=quiz.subject,
        schedule_start=quiz.schedule_start,
        schedule_end=quiz.schedule_end,
        duration_minutes=quiz.duration_minutes,
        status=quiz.status,
        created_by=quiz.created_by,
        created_at=quiz.created_at,
        question_count=question_count,
    )


@router.get("", response_model=list[QuizOut])
def list_quizzes(
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    quiz_type: Optional[str] = None,
    status_: Optional[str] = None,
):
    stmt = (
        select(Quiz, func.count(QuizQuestion.id))
        .outerjoin(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
        .where(Quiz.college_id == user.college_id)
        .group_by(Quiz.id)
    )
    if quiz_type is not None:
        stmt = stmt.where(Quiz.quiz_type == quiz_type)
    if status_ is not None:
        stmt = stmt.where(Quiz.status == status_)
    rows = db.execute(stmt.order_by(Quiz.id.desc())).all()
    return [_serialize(quiz, count) for quiz, count in rows]


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    count = db.execute(
        select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz.id)
    ).scalar_one()
    return _serialize(quiz, count)


@router.post("", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
def create_quiz(payload: QuizCreate, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    quiz = Quiz(college_id=user.college_id, created_by=user.id, **payload.model_dump())
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return _serialize(quiz)


@router.patch("/{quiz_id}", response_model=QuizOut)
def update_quiz(
    quiz_id: int,
    payload: QuizUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(quiz, field, value)
    db.commit()
    db.refresh(quiz)
    count = db.execute(
        select(func.count(QuizQuestion.id)).where(QuizQuestion.quiz_id == quiz.id)
    ).scalar_one()
    return _serialize(quiz, count)


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(quiz_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    db.delete(quiz)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Quiz is still referenced (exam links, class targets, or attempts) — remove those first",
        )


# ------------------------------------------------------------- quiz questions

@router.get("/{quiz_id}/questions", response_model=list[QuizQuestionOut])
def list_quiz_questions(quiz_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    rows = db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz.id)
        .options(selectinload(QuizQuestion.question))
        .order_by(QuizQuestion.order_index)
    ).scalars().all()
    return [
        QuizQuestionOut(
            id=r.id,
            question_id=r.question_id,
            order_index=r.order_index,
            marks=r.marks,
            text=r.question.text,
            question_type=r.question.question_type,
            difficulty=r.question.difficulty,
        )
        for r in rows
    ]


@router.post("/{quiz_id}/questions", response_model=QuizQuestionOut, status_code=status.HTTP_201_CREATED)
def add_quiz_question(
    quiz_id: int,
    payload: QuizQuestionAdd,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    question = db.execute(
        select(Question).where(Question.id == payload.question_id, Question.college_id == user.college_id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "question_id does not exist for this college")

    row = QuizQuestion(
        quiz_id=quiz.id,
        question_id=question.id,
        order_index=payload.order_index,
        marks=payload.marks if payload.marks is not None else question.marks,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This question is already in the quiz")
    db.refresh(row)
    return QuizQuestionOut(
        id=row.id, question_id=row.question_id, order_index=row.order_index, marks=row.marks,
        text=question.text, question_type=question.question_type, difficulty=question.difficulty,
    )


@router.patch("/{quiz_id}/questions/{quiz_question_id}", response_model=QuizQuestionOut)
def update_quiz_question(
    quiz_id: int,
    quiz_question_id: int,
    payload: QuizQuestionReorder,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    row = db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.id == quiz_question_id, QuizQuestion.quiz_id == quiz.id)
        .options(selectinload(QuizQuestion.question))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz question not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return QuizQuestionOut(
        id=row.id, question_id=row.question_id, order_index=row.order_index, marks=row.marks,
        text=row.question.text, question_type=row.question.question_type, difficulty=row.question.difficulty,
    )


@router.delete("/{quiz_id}/questions/{quiz_question_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_quiz_question(
    quiz_id: int,
    quiz_question_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    row = db.execute(
        select(QuizQuestion).where(QuizQuestion.id == quiz_question_id, QuizQuestion.quiz_id == quiz.id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz question not found")
    db.delete(row)
    db.commit()


# ---------------------------------------------------------------- class test
# A "class test" is simply a quiz (quiz_type='class') assigned directly to
# one or more classes — no registration/payment/exam wrapper needed.

@router.get("/{quiz_id}/class-targets", response_model=list[QuizClassTargetOut])
def list_class_targets(quiz_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    rows = db.execute(
        select(QuizClassTarget)
        .where(QuizClassTarget.quiz_id == quiz.id)
        .options(selectinload(QuizClassTarget.class_))
    ).scalars().all()
    return [
        QuizClassTargetOut(
            id=r.id, quiz_id=r.quiz_id, class_id=r.class_id, class_name=r.class_.name,
            assigned_by=r.assigned_by, assigned_at=r.assigned_at,
        )
        for r in rows
    ]


@router.post("/{quiz_id}/class-targets", response_model=QuizClassTargetOut, status_code=status.HTTP_201_CREATED)
def assign_class_target(
    quiz_id: int,
    payload: QuizClassTargetAssign,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    if quiz.quiz_type != "class":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only quizzes with quiz_type='class' can be assigned to classes")

    klass = db.execute(
        select(Class).where(Class.id == payload.class_id, Class.college_id == user.college_id)
    ).scalar_one_or_none()
    if klass is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "class_id does not exist for this college")

    row = QuizClassTarget(
        quiz_id=quiz.id,
        class_id=klass.id,
        assigned_by=user.id,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz is already assigned to that class")
    db.refresh(row)
    return QuizClassTargetOut(
        id=row.id, quiz_id=row.quiz_id, class_id=row.class_id, class_name=klass.name,
        assigned_by=row.assigned_by, assigned_at=row.assigned_at,
    )


@router.delete("/{quiz_id}/class-targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_class_target(
    quiz_id: int,
    target_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = _get_quiz_or_404(db, quiz_id, user.college_id)
    row = db.execute(
        select(QuizClassTarget).where(QuizClassTarget.id == target_id, QuizClassTarget.quiz_id == quiz.id)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class target not found")
    db.delete(row)
    db.commit()
