import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, CurrentUser, DbSession, require_roles
from models.auth import User
from models.problem import Problem, ProblemTopic, TestCase
from schemas.problem import (
    ProblemCreate,
    ProblemListItem,
    ProblemOut,
    ProblemUpdate,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
)

router = APIRouter(prefix="/problems", tags=["problems"])


def _load_options():
    return (
        selectinload(Problem.problem_topics).selectinload(ProblemTopic.topic),
        selectinload(Problem.test_cases),
    )


def _get_problem_or_404(db: DbSession, problem_id: int, college_id: int) -> Problem:
    problem = db.execute(
        select(Problem)
        .where(Problem.id == problem_id, Problem.college_id == college_id)
        .options(*_load_options())
    ).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    return problem


def _serialize(problem: Problem, *, reveal_hidden: bool) -> ProblemOut:
    return ProblemOut(
        id=problem.id,
        uuid=problem.uuid,
        college_id=problem.college_id,
        title=problem.title,
        slug=problem.slug,
        description=problem.description,
        constraints=problem.constraints,
        starter_code=problem.starter_code,
        difficulty=problem.difficulty,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_kb=problem.memory_limit_kb,
        allowed_languages=problem.allowed_languages,
        default_language=problem.default_language,
        is_active=problem.is_active,
        created_by=problem.created_by,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
        topics=[pt.topic for pt in problem.problem_topics],
        test_cases=[
            TestCaseOut.from_test_case(tc, reveal_hidden=reveal_hidden)
            for tc in problem.test_cases
        ],
    )


def _set_topics(db: DbSession, problem: Problem, topic_ids: list[int]) -> None:
    db.query(ProblemTopic).filter(ProblemTopic.problem_id == problem.id).delete()
    for topic_id in topic_ids:
        db.add(ProblemTopic(problem_id=problem.id, topic_id=topic_id))


# ------------------------------------------------------------------- problems

@router.get("", response_model=list[ProblemListItem])
def list_problems(
    db: DbSession,
    user: CurrentUser,
    topic_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    is_active: Optional[bool] = True,
):
    stmt = select(Problem).where(Problem.college_id == user.college_id)
    if is_active is not None:
        stmt = stmt.where(Problem.is_active == is_active)
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    if topic_id:
        stmt = stmt.join(ProblemTopic).where(ProblemTopic.topic_id == topic_id)
    return db.execute(stmt.order_by(Problem.id)).scalars().all()


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: int, db: DbSession, user: CurrentUser):
    problem = _get_problem_or_404(db, problem_id, user.college_id)
    reveal_hidden = user.role.name in STAFF_ROLES
    return _serialize(problem, reveal_hidden=reveal_hidden)


@router.post("", response_model=ProblemOut, status_code=status.HTTP_201_CREATED)
def create_problem(
    payload: ProblemCreate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    problem = Problem(
        college_id=user.college_id,
        uuid=str(uuid_lib.uuid4()),
        created_by=user.id,
        **payload.model_dump(exclude={"topic_ids"}),
    )
    db.add(problem)
    db.flush()
    _set_topics(db, problem, payload.topic_ids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Slug already exists for this college, or an invalid topic_id was given",
        )
    problem = _get_problem_or_404(db, problem.id, user.college_id)
    return _serialize(problem, reveal_hidden=True)


@router.patch("/{problem_id}", response_model=ProblemOut)
def update_problem(
    problem_id: int,
    payload: ProblemUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    problem = _get_problem_or_404(db, problem_id, user.college_id)
    data = payload.model_dump(exclude_unset=True, exclude={"topic_ids"})
    for field, value in data.items():
        setattr(problem, field, value)
    if payload.topic_ids is not None:
        _set_topics(db, problem, payload.topic_ids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Slug already exists for this college, or an invalid topic_id was given",
        )
    problem = _get_problem_or_404(db, problem_id, user.college_id)
    return _serialize(problem, reveal_hidden=True)


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_problem(
    problem_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    """Soft delete only: Problem's relationships have no delete cascade
    configured, so a hard delete would fail (or orphan rows) once test
    cases / submissions exist. This just flips is_active off."""
    problem = _get_problem_or_404(db, problem_id, user.college_id)
    problem.is_active = False
    db.commit()


# ------------------------------------------------------------------ test cases

@router.get("/{problem_id}/test-cases", response_model=list[TestCaseOut])
def list_test_cases(
    problem_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    problem = _get_problem_or_404(db, problem_id, user.college_id)
    return [TestCaseOut.from_test_case(tc, reveal_hidden=True) for tc in problem.test_cases]


@router.post(
    "/{problem_id}/test-cases",
    response_model=TestCaseOut,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    problem_id: int,
    payload: TestCaseCreate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    _get_problem_or_404(db, problem_id, user.college_id)
    test_case = TestCase(problem_id=problem_id, **payload.model_dump())
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return TestCaseOut.from_test_case(test_case, reveal_hidden=True)


@router.patch("/{problem_id}/test-cases/{test_case_id}", response_model=TestCaseOut)
def update_test_case(
    problem_id: int,
    test_case_id: int,
    payload: TestCaseUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    _get_problem_or_404(db, problem_id, user.college_id)
    test_case = db.get(TestCase, test_case_id)
    if test_case is None or test_case.problem_id != problem_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test case not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(test_case, field, value)
    db.commit()
    db.refresh(test_case)
    return TestCaseOut.from_test_case(test_case, reveal_hidden=True)


@router.delete("/{problem_id}/test-cases/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(
    problem_id: int,
    test_case_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    _get_problem_or_404(db, problem_id, user.college_id)
    test_case = db.get(TestCase, test_case_id)
    if test_case is None or test_case.problem_id != problem_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test case not found")
    db.delete(test_case)
    db.commit()
