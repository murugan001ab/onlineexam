from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.deps import STAFF_ROLES, CurrentUser, DbSession, require_roles
from models.auth import User
from models.catalog import Topic
from schemas.catalog import TopicCreate, TopicOut, TopicTree, TopicUpdate

router = APIRouter(prefix="/topics", tags=["topics"])


def _get_topic_or_404(db: DbSession, topic_id: int, college_id: int) -> Topic:
    topic = db.execute(
        select(Topic).where(Topic.id == topic_id, Topic.college_id == college_id)
    ).scalar_one_or_none()
    if topic is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
    return topic


def _validate_parent(db: DbSession, college_id: int, parent_id: Optional[int], self_id: Optional[int]) -> None:
    if parent_id is None:
        return
    if parent_id == self_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A topic cannot be its own parent")
    parent = db.execute(
        select(Topic).where(Topic.id == parent_id, Topic.college_id == college_id)
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "parent_id does not exist for this college")


@router.get("", response_model=list[TopicOut])
def list_topics(db: DbSession, user: CurrentUser):
    stmt = select(Topic).where(Topic.college_id == user.college_id).order_by(Topic.order_index, Topic.name)
    return db.execute(stmt).scalars().all()


@router.get("/tree", response_model=list[TopicTree])
def list_topics_tree(db: DbSession, user: CurrentUser):
    """Same topics, nested under their parents. Root topics only at the
    top level; children are attached to each node."""
    topics = db.execute(
        select(Topic).where(Topic.college_id == user.college_id).order_by(Topic.order_index, Topic.name)
    ).scalars().all()

    nodes: dict[int, TopicTree] = {
        t.id: TopicTree.model_validate(t, from_attributes=True) for t in topics
    }
    roots: list[TopicTree] = []
    for t in topics:
        node = nodes[t.id]
        if t.parent_id is not None and t.parent_id in nodes:
            nodes[t.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get("/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: int, db: DbSession, user: CurrentUser):
    return _get_topic_or_404(db, topic_id, user.college_id)


@router.post("", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(
    payload: TopicCreate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    _validate_parent(db, user.college_id, payload.parent_id, self_id=None)
    topic = Topic(college_id=user.college_id, **payload.model_dump())
    db.add(topic)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already exists for this college")
    db.refresh(topic)
    return topic


@router.patch("/{topic_id}", response_model=TopicOut)
def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    topic = _get_topic_or_404(db, topic_id, user.college_id)
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data:
        _validate_parent(db, user.college_id, data["parent_id"], self_id=topic.id)
    for field, value in data.items():
        setattr(topic, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already exists for this college")
    db.refresh(topic)
    return topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(
    topic_id: int,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    topic = _get_topic_or_404(db, topic_id, user.college_id)
    db.delete(topic)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Topic is still referenced (child topics, questions, problems, or exam weights) — remove those first",
        )
