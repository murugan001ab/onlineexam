from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.auth import User
from models.attempt import ExamAnswer, ExamAttempt
from models.entrance import ExamRegistration
from models.exam import Exam, ExamQuiz
from models.question import Question, QuizQuestion
from models.student import Student
from schemas.attempt import AnswerSubmit, ExamAnswerOut, ExamAnswerReview, ExamAttemptOut
from schemas.question import QuestionPublicOut

student_router = APIRouter(prefix="/exam-attempts", tags=["exam-attempts"])
admin_router = APIRouter(prefix="/admin", tags=["exam-attempts"])

RequireStudent = Depends(require_roles("student"))


def _get_student_or_404(db: DbSession, user: User) -> Student:
    student = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return student


def _serialize_attempt(attempt: ExamAttempt) -> ExamAttemptOut:
    return ExamAttemptOut(
        id=attempt.id,
        exam_id=attempt.exam_id,
        exam_name=attempt.exam.name if attempt.exam else None,
        student_id=attempt.student_id,
        status=attempt.status,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        duration_minutes=attempt.exam.duration_minutes if attempt.exam else None,
        score=attempt.score,
        max_score=attempt.max_score,
    )


def _expire_if_overdue(db: DbSession, attempt: ExamAttempt) -> None:
    if attempt.status != "in_progress" or attempt.started_at is None:
        return
    exam = attempt.exam
    deadline = None
    if exam.duration_minutes is not None:
        deadline = attempt.started_at + timedelta(minutes=exam.duration_minutes)
    if exam.ends_at is not None and (deadline is None or exam.ends_at < deadline):
        deadline = exam.ends_at
    if deadline is not None and datetime.now(timezone.utc) > deadline:
        attempt.status = "expired"
        db.commit()


def _get_own_attempt_or_404(db: DbSession, attempt_id: int, student: Student) -> ExamAttempt:
    attempt = db.execute(
        select(ExamAttempt)
        .where(ExamAttempt.id == attempt_id, ExamAttempt.student_id == student.id)
        .options(selectinload(ExamAttempt.exam))
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    return attempt


def _compiled_questions(db: DbSession, exam_id: int) -> list[QuizQuestion]:
    """All questions across every quiz linked to this exam, in exam-quiz order
    then in-quiz order, de-duplicated by question id."""
    rows = db.execute(
        select(QuizQuestion)
        .join(ExamQuiz, ExamQuiz.quiz_id == QuizQuestion.quiz_id)
        .where(ExamQuiz.exam_id == exam_id)
        .options(selectinload(QuizQuestion.question))
        .order_by(ExamQuiz.order_index, QuizQuestion.order_index)
    ).scalars().all()
    seen: set[int] = set()
    unique: list[QuizQuestion] = []
    for r in rows:
        if r.question_id not in seen:
            seen.add(r.question_id)
            unique.append(r)
    return unique


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
# Student-facing: start, answer, submit
# ==================================================================

@student_router.post("/{exam_id}/start", response_model=ExamAttemptOut, status_code=status.HTTP_201_CREATED)
def start_attempt(exam_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)

    exam = db.execute(
        select(Exam).where(Exam.id == exam_id, Exam.college_id == student.college_id)
    ).scalar_one_or_none()
    if exam is None or exam.status not in ("published", "running"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Exam not found or not currently open")

    registration = db.execute(
        select(ExamRegistration).where(
            ExamRegistration.exam_id == exam.id,
            ExamRegistration.student_id == student.id,
            ExamRegistration.status == "confirmed",
        )
    ).scalar_one_or_none()
    if registration is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have a confirmed registration for this exam")

    existing = db.execute(
        select(ExamAttempt)
        .where(ExamAttempt.exam_id == exam.id, ExamAttempt.student_id == student.id)
        .options(selectinload(ExamAttempt.exam))
    ).scalar_one_or_none()
    if existing is not None:
        _expire_if_overdue(db, existing)
        return _serialize_attempt(existing)

    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=student.id,
        started_at=datetime.now(timezone.utc),
        status="in_progress",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    attempt.exam = exam
    return _serialize_attempt(attempt)


@student_router.get("/{attempt_id}", response_model=ExamAttemptOut)
def get_my_attempt(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    return _serialize_attempt(attempt)


@student_router.get("/{attempt_id}/questions", response_model=list[QuestionPublicOut])
def get_attempt_questions(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status not in ("in_progress",):
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not in progress")
    rows = _compiled_questions(db, attempt.exam_id)
    return [
        QuestionPublicOut(
            id=r.question.id, topic_id=r.question.topic_id, text=r.question.text,
            question_type=r.question.question_type, options=r.question.options,
            difficulty=r.question.difficulty, marks=r.marks or r.question.marks,
        )
        for r in rows
    ]


@student_router.post("/{attempt_id}/answers", response_model=ExamAnswerOut)
def submit_answer(attempt_id: int, payload: AnswerSubmit, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is not in progress")

    question = db.execute(
        select(Question)
        .join(QuizQuestion, QuizQuestion.question_id == Question.id)
        .join(ExamQuiz, ExamQuiz.quiz_id == QuizQuestion.quiz_id)
        .where(ExamQuiz.exam_id == attempt.exam_id, Question.id == payload.question_id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This question is not part of this exam")

    is_correct, marks = _grade_answer(question, payload.answer)

    row = db.execute(
        select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id, ExamAnswer.question_id == question.id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = ExamAnswer(
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


@student_router.post("/{attempt_id}/submit", response_model=ExamAttemptOut)
def submit_attempt(attempt_id: int, db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    attempt = _get_own_attempt_or_404(db, attempt_id, student)
    _expire_if_overdue(db, attempt)
    if attempt.status not in ("in_progress", "expired"):
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt cannot be submitted")

    answers = db.execute(select(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id)).scalars().all()
    questions = _compiled_questions(db, attempt.exam_id)

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

@admin_router.get("/exams/{exam_id}/attempts", response_model=list[ExamAttemptOut])
def list_exam_attempts(
    exam_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    status_: Optional[str] = None,
):
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    stmt = (
        select(ExamAttempt)
        .where(ExamAttempt.exam_id == exam.id)
        .options(selectinload(ExamAttempt.exam))
    )
    if status_ is not None:
        stmt = stmt.where(ExamAttempt.status == status_)
    rows = db.execute(stmt.order_by(ExamAttempt.id.desc())).scalars().all()
    return [_serialize_attempt(a) for a in rows]


@admin_router.get("/exams/{exam_id}/attempts/{attempt_id}/answers", response_model=list[ExamAnswerReview])
def review_attempt_answers(
    exam_id: int,
    attempt_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
    attempt = db.execute(
        select(ExamAttempt).where(ExamAttempt.id == attempt_id, ExamAttempt.exam_id == exam.id)
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")

    rows = db.execute(
        select(ExamAnswer)
        .where(ExamAnswer.attempt_id == attempt.id)
        .options(selectinload(ExamAnswer.question))
    ).scalars().all()
    return [
        ExamAnswerReview(
            id=r.id, question_id=r.question_id, answer=r.answer, is_correct=r.is_correct,
            marks=r.marks, answered_at=r.answered_at,
            question_text=r.question.text, correct_answer=r.question.correct_answer,
        )
        for r in rows
    ]
