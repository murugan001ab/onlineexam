"""Import every model here so Base.metadata is fully populated for Alembic autogenerate,
and so string-based relationship() references resolve correctly across modules."""

from models.college import College
from models.auth import Profile, Role, Permission, RolePermission, User
from models.organization import Department, Class, StaffDepartment, StaffClass
from models.student import Student, StudentClass
from models.catalog import ExamType, Topic
from models.question import Question, QuizQuestion
from models.quiz import Quiz, QuizClassTarget
from models.entrance import ExamSlot, ExamRegistration, SlotHold
from models.payment import Payment
from models.exam import Exam, ExamQuiz, ExamTopicWeight, ExamInvitation
from models.attempt import ExamAttempt, ExamAnswer
from models.proctoring import ProctoringEvent, ProctoringSnapshot
from models.problem import Problem, ProblemTopic, TestCase, Submission, ProblemUnlock
from models.training import (
    TrainingAssignment,
    TrainingAttempt,
    TrainingSubmission,
    PromptEvaluation,
)

__all__ = [
    "College",
    "Profile",
    "Role",
    "Permission",
    "RolePermission",
    "User",
    "Department",
    "Class",
    "StaffDepartment",
    "StaffClass",
    "Student",
    "StudentClass",
    "ExamType",
    "Topic",
    "Question",
    "QuizQuestion",
    "Quiz",
    "QuizClassTarget",
    "ExamSlot",
    "ExamRegistration",
    "SlotHold",
    "Payment",
    "Exam",
    "ExamQuiz",
    "ExamTopicWeight",
    "ExamInvitation",
    "ExamAttempt",
    "ExamAnswer",
    "ProctoringEvent",
    "ProctoringSnapshot",
    "Problem",
    "ProblemTopic",
    "TestCase",
    "Submission",
    "ProblemUnlock",
    "TrainingAssignment",
    "TrainingAttempt",
    "TrainingSubmission",
    "PromptEvaluation",
]
