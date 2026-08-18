from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.auth import User
from models.organization import Class
from models.question import Question, QuizQuestion
from models.quiz import Quiz, QuizClassTarget
from models.quiz_attempt import QuizAnswer, QuizAttempt
from models.student import Student, StudentClass
from schemas.question import QuestionPublicOut
from schemas.quiz_attempt import (
    QuizAnswerOut,
    QuizAnswerReview,
    QuizAnswerSubmit,
    QuizAttemptOut,
    QuizAvailableOut,
)

student_router = APIRouter(prefix="/class-quizzes", tags=["quiz-attempts"])
admin_router = APIRouter(prefix="/admin/quizzes", tags=["quiz-attempts"])

RequireStudent = Depends(require_roles("student"))


def _get_student_or_404(db: DbSession, user: User) -> Student:
    student = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return student


def _active_class_ids(db: DbSession, student_id: int) -> list[int]:
    return list(
        db.execute(
            select(StudentClass.class_id).where(
                StudentClass.student_id == student_id, StudentClass.left_at.is_(None)
            )
        ).scalars().all()
    )


def _serialize_attempt(attempt: QuizAttempt) -> QuizAttemptOut:
    return QuizAttemptOut(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        quiz_name=attempt.quiz.name if attempt.quiz else None,
        class_id=attempt.class_id,
        student_id=attempt.student_id,
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        duration_minutes=attempt.quiz.duration_minutes if attempt.quiz else None,
        score=attempt.score,
        max_score=attempt.max_score,
    )


def _expire_if_overdue(db: DbSession, attempt: QuizAttempt) -> None:
    if attempt.status != "in_progress" or attempt.started_at is None:
        return
    quiz = attempt.quiz
    deadline = None
    if quiz.duration_minutes is not None:
        deadline = attempt.started_at + timedelta(minutes=quiz.duration_minutes)
    if quiz.schedule_end is not None and (deadline is None or quiz.schedule_end < deadline):
        deadline = quiz.schedule_end
    if deadline is not None and datetime.now(timezone.utc) > deadline:
        attempt.status = "expired"
        db.commit()


def _get_own_attempt_or_404(db: DbSession, attempt_id: int, student: Student) -> QuizAttempt:
    attempt = db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.id == attempt_id, QuizAttempt.student_id == student.id)
        .options(selectinload(QuizAttempt.quiz))
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    return attempt


def _compiled_questions(db: DbSession, quiz_id: int) -> list[QuizQuestion]:
    return db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .options(selectinload(QuizQuestion.question))
        .order_by(QuizQuestion.order_index)
    ).scalars().all()


def _grade_answer(question: Question, answer: Any) -> tuple[bool, Decimal]:
    correct = question.correct_answer
    if question.question_type == "multiple_choice":
        try:
            is_correct = set(answer) == set(correct)
        except TypeError:
            is_correct = answer == correct
    else:
        is_correct = answer == correct
    marks = Decimal(question.marks) if is_correct else Decimal(0)
    return is_correct, marks


# ==================================================================
# Student-facing: browse, start, answer, submit
# ==================================================================

@student_router.get("", response_model=list[QuizAvailableOut])
def list_available_quizzes(db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    class_ids = _active_class_ids(db, student.id)
    if not class_ids:
        return []

    rows = db.execute(
        select(QuizClassTarget, Quiz, Class)
        .join(Quiz, Quiz.id == QuizClassTarget.quiz_id)
        .join(Class, Class.id == QuizClassTarget.class_id)
        .where(
            QuizClassTarget.class_id.in_(class_ids),
            Quiz.status == "published",
            Quiz.quiz_type == "class",
        )
    ).all()
    if not rows:
        return []

    quiz_ids = [quiz.id for _, quiz, _ in rows]
    attempts = {
        a.quiz_id: a
        for a in db.execute(
            select(QuizAttempt).where(
                QuizAttempt.student_id == student.id, QuizAttempt.quiz_id.in_(quiz_ids)
            )
        ).scalars().all()
    }

    return [
        QuizAvailableOut(
            id=quiz.id,
            name=quiz.name,
            description=quiz.description,
            subject=quiz.subject,
            schedule_start=quiz.schedule_start,
            schedule_end=quiz.schedule_end,
            duration_minutes=quiz.duration_minutes,
            class_id=klass.id,
            class_name=klass.name,
            attempt_id=attempts[quiz.id].id if quiz.id in attempts else None,
            attempt_status=attempts[quiz.id].status if quiz.id in attempts else None,
        )
        for _, quiz, klass in rows
    ]


@student_router.post("/{quiz_id}/start", response_model=QuizAttemptOut, status_code=status.HTTP_201_CREATED)
def start_attempt(quiz_id: int, db: DbSession, user: User = RequireStudent):
    """Idempotent: returns the existing attempt if one already exists,
    rather than restarting the timer."""
    student = _get_student_or_404(db, user)

    quiz = db.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.college_id == student.college_id)
    ).scalar_one_or_none()
    if quiz is None or quiz.quiz_type != "class" or quiz.status != "published":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quiz not found or not currently open")

    now = datetime.now(timezone.utc)
    if quiz.schedule_start is not None and now < quiz.schedule_start:
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz has not started yet")
    if quiz.schedule_end is not None and now > quiz.schedule_end:
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz window has closed")

    target = db.execute(
        select(QuizClassTarget)
        .join(StudentClass, StudentClass.class_id == QuizClassTarget.class_id)
        .where(
            QuizClassTarget.quiz_id == quiz.id,
            StudentClass.student_id == student.id,
            StudentClass.left_at.is_(None),
        )
    ).scalars().first()
    if target is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This quiz is not assigned to any of your classes")

    existing = db.execute(
        select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id, QuizAttempt.student_id == student.id)
    ).scalar_one_or_none()
    if existing is not None:
        existing.quiz = quiz
        _expire_if_overdue(db, existing)
        return _serialize_attempt(existing)

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=student.id,
        class_id=target.class_id,
        started_at=now,
        status="in_progress",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    attempt.quiz = quiz
    return _serialize_attempt(attempt)


@student_router.get("/attempts/{attempt_id}", response_model=QuizAttemptOut)
def get_my_attempt(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    return _serialize_attempt(attempt)


@student_router.get("/attempts/{attempt_id}/questions", response_model=list[QuestionPublicOut])
def get_attempt_questions(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not in progress")
    rows = _compiled_questions(db, attempt.quiz_id)
    return [
        QuestionPublicOut(
            id=r.question.id, topic_id=r.question.topic_id, text=r.question.text,
            question_type=r.question.question_type, options=r.question.options,
            difficulty=r.question.difficulty, marks=r.marks or r.question.marks,
        )
        for r in rows
    ]


@student_router.post("/attempts/{attempt_id}/answers", response_model=QuizAnswerOut)
def submit_answer(attempt_id: int, payload: QuizAnswerSubmit, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not in progress")

    question = db.execute(
        select(Question)
        .join(QuizQuestion, QuizQuestion.question_id == Question.id)
        .where(QuizQuestion.quiz_id == attempt.quiz_id, Question.id == payload.question_id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This question is not part of this quiz")

    is_correct, marks = _grade_answer(question, payload.answer)

    row = db.execute(
        select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id, QuizAnswer.question_id == question.id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = QuizAnswer(
            attempt_id=attempt.id, question_id=question.id, answer=payload.answer,
            is_correct=is_correct, marks=marks, answered_at=now,
        )
        db.add(row)
    else:
        row.answer = payload.answer
        row.is_correct = is_correct
        row.marks = marks
        row.answered_at = now
    db.commit()
    db.refresh(row)
    return row


@student_router.post("/attempts/{attempt_id}/submit", response_model=QuizAttemptOut)
def submit_attempt(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status not in ("in_progress", "expired"):
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt cannot be submitted")

    answers = db.execute(select(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id)).scalars().all()
    questions = _compiled_questions(db, attempt.quiz_id)

    attempt.score = sum((a.marks or Decimal(0)) for a in answers)
    attempt.max_score = sum(Decimal(q.marks or q.question.marks) for q in questions)
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attempt)
    return _serialize_attempt(attempt)


# ==================================================================
# Admin/staff: oversight and grading review
# ==================================================================

@admin_router.get("/{quiz_id}/attempts", response_model=list[QuizAttemptOut])
def list_quiz_attempts(
    quiz_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    status_: Optional[str] = None,
):
    quiz = db.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.college_id == user.college_id)
    ).scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    stmt = select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id).options(selectinload(QuizAttempt.quiz))
    if status_ is not None:
        stmt = stmt.where(QuizAttempt.status == status_)
    rows = db.execute(stmt.order_by(QuizAttempt.id.desc())).scalars().all()
    return [_serialize_attempt(a) for a in rows]


@admin_router.get("/{quiz_id}/attempts/{attempt_id}/answers", response_model=list[QuizAnswerReview])
def review_attempt_answers(
    quiz_id: int,
    attempt_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    quiz = db.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.college_id == user.college_id)
    ).scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    attempt = db.execute(
        select(QuizAttempt).where(QuizAttempt.id == attempt_id, QuizAttempt.quiz_id == quiz.id)
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")

    rows = db.execute(
        select(QuizAnswer)
        .where(QuizAnswer.attempt_id == attempt.id)
        .options(selectinload(QuizAnswer.question))
    ).scalars().all()
    return [
        QuizAnswerReview(
            id=r.id, question_id=r.question_id, answer=r.answer, is_correct=r.is_correct,
            marks=r.marks, answered_at=r.answered_at,
            question_text=r.question.text, correct_answer=r.question.correct_answer,
        )
        for r in rows
    ]
