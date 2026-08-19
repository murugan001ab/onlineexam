from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.auth import User
from models.catalog import Topic
from models.question import Question
from schemas.question import QuestionCreate, QuestionOut, QuestionUpdate, _validate_options_and_answer
from utils.storage import file_url, save_upload

router = APIRouter(prefix="/admin/questions", tags=["questions"])


def _get_question_or_404(db: DbSession, question_id: int, college_id: int) -> Question:
    question = db.execute(
        select(Question).where(Question.id == question_id, Question.college_id == college_id)
    ).scalar_one_or_none()
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    return question


def _validate_topic(db: DbSession, college_id: int, topic_id: Optional[int]) -> None:
    if topic_id is None:
        return
    topic = db.execute(
        select(Topic).where(Topic.id == topic_id, Topic.college_id == college_id)
    ).scalar_one_or_none()
    if topic is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "topic_id does not exist for this college")


def _validate_answer_key(question: Question, data: dict) -> None:
    """Re-runs the options/correct_answer consistency check from
    schemas.question against the *merged* state (existing row + incoming
    PATCH fields). QuestionUpdate only validates fields present in the same
    request, so e.g. flipping question_type from single_choice to
    true_false without touching options/correct_answer would otherwise slip
    through with a stale answer key."""
    question_type = data.get("question_type", question.question_type)
    options = data.get("options", question.options)
    correct_answer = data.get("correct_answer", question.correct_answer)
    try:
        _validate_options_and_answer(question_type, options, correct_answer)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("", response_model=list[QuestionOut])
def list_questions(
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    topic_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    is_active: Optional[bool] = True,
):
    stmt = select(Question).where(Question.college_id == user.college_id)
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    if question_type is not None:
        stmt = stmt.where(Question.question_type == question_type)
    if is_active is not None:
        stmt = stmt.where(Question.is_active == is_active)
    return db.execute(stmt.order_by(Question.id.desc())).scalars().all()


@router.get("/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    return _get_question_or_404(db, question_id, user.college_id)


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(
    payload: QuestionCreate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    _validate_topic(db, user.college_id, payload.topic_id)
    question = Question(college_id=user.college_id, created_by=user.id, **payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.patch("/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    question = _get_question_or_404(db, question_id, user.college_id)
    data = payload.model_dump(exclude_unset=True)
    if "topic_id" in data:
        _validate_topic(db, user.college_id, data["topic_id"])
    if data.keys() & {"question_type", "options", "correct_answer"}:
        _validate_answer_key(question, data)
    for field, value in data.items():
        setattr(question, field, value)
    db.commit()
    db.refresh(question)
    return question


@router.post("/upload-image")
async def upload_question_image(
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
    file: UploadFile = File(...),
):
    """Uploads a question diagram/figure and returns a servable URL. The
    frontend calls this first, then sends the returned url as image_url on
    QuestionCreate/QuestionUpdate."""
    relative_path, _, _ = await save_upload(file, subdir=f"questions/{user.college_id}")
    return {"image_url": file_url(relative_path)}


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_question(
    question_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    """Soft delete: questions may already be referenced by quiz_questions /
    exam_answers, so a hard delete would fail or orphan grading history."""
    question = _get_question_or_404(db, question_id, user.college_id)
    question.is_active = False
    db.commit()
