from typing import Any, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.mixins import TimestampMixin


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), nullable=False)
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id"))

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # single_choice | multiple_choice | true_false
    question_type: Mapped[Optional[str]] = mapped_column(String(30))

    options: Mapped[Optional[Any]] = mapped_column(JSONB)
    correct_answer: Mapped[Optional[Any]] = mapped_column(JSONB)
    explanation: Mapped[Optional[str]] = mapped_column(Text)

    # easy | medium | hard
    difficulty: Mapped[Optional[str]] = mapped_column(String(30))
    marks: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    topic: Mapped[Optional["Topic"]] = relationship(back_populates="questions")
    quiz_questions: Mapped[List["QuizQuestion"]] = relationship(back_populates="question")
    exam_answers: Mapped[List["ExamAnswer"]] = relationship(back_populates="question")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("quiz_id", "question_id", name="uq_quiz_question"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)

    order_index: Mapped[Optional[int]] = mapped_column(Integer)
    marks: Mapped[Optional[int]] = mapped_column(Integer)

    quiz: Mapped["Quiz"] = relationship(back_populates="quiz_questions")
    question: Mapped["Question"] = relationship(back_populates="quiz_questions")
