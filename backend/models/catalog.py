from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class ExamType(Base, TimestampMixin):
    __tablename__ = "exam_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    exams: Mapped[List["Exam"]] = relationship(back_populates="exam_type")


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("college_id", "slug", name="uq_topic_college_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id"))
    order_index: Mapped[Optional[int]] = mapped_column(Integer)

    parent: Mapped[Optional["Topic"]] = relationship(remote_side="Topic.id", back_populates="children")
    children: Mapped[List["Topic"]] = relationship(back_populates="parent")
    questions: Mapped[List["Question"]] = relationship(back_populates="topic")
    exam_topic_weights: Mapped[List["ExamTopicWeight"]] = relationship(back_populates="topic")
