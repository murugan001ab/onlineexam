"""Create idempotent demo data for local development.

Run after migrations from the backend directory:
    python -m scripts.seed_demo

Demo credentials (password for every account): Demo@12345
  superadmin, admin, staff, student
"""
from datetime import timedelta, timezone, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from core.database import SessionLocal
from core.security import hash_password
from models.auth import Profile, Role, User
from models.catalog import ExamType, Topic
from models.college import College
from models.entrance import ExamRegistration, ExamSlot
from models.exam import Exam, ExamQuiz, ExamTopicWeight
from models.organization import Class, Department, StaffClass, StaffDepartment
from models.problem import Problem, ProblemTopic, TestCase
from models.question import Question, QuizQuestion
from models.quiz import Quiz, QuizClassTarget
from models.student import Student, StudentClass
from models.training import TrainingAssignment

PASSWORD = "Demo@12345"


def one(db, model, *criteria):
    return db.execute(select(model).where(*criteria)).scalar_one_or_none()


def user(db, role, username, name, college=None, email=None):
    existing = one(db, User, User.username == username)
    if existing:
        return existing
    profile = Profile(name=name, email=email) if False else Profile(name=name)
    db.add(profile); db.flush()
    record = User(college_id=college.id if college else None, profile_id=profile.id, role_id=role.id,
                  username=username, email=email, password_hash=hash_password(PASSWORD), is_active=True)
    db.add(record); db.flush()
    return record


def main():
    db = SessionLocal()
    try:
        roles = {}
        for name in ("super_admin", "admin", "staff", "student"):
            role = one(db, Role, Role.name == name)
            if not role:
                role = Role(name=name, description=f"Demo {name.replace('_', ' ')} role")
                db.add(role); db.flush()
            roles[name] = role

        super_admin = user(db, roles["super_admin"], "superadmin", "Demo Super Admin", email="superadmin@example.test")
        college = one(db, College, College.code == "DEMO")
        if not college:
            college = College(name="Demo Engineering College", code="DEMO", city="Chennai", state="Tamil Nadu", email="office@example.test", is_active=True)
            db.add(college); db.flush()
        admin = user(db, roles["admin"], "admin", "Demo College Admin", college, "admin@example.test")
        staff = user(db, roles["staff"], "staff", "Priya Faculty", college, "staff@example.test")
        student_user = user(db, roles["student"], "student", "Arun Student", college, "student@example.test")

        department = one(db, Department, Department.college_id == college.id, Department.code == "CSE")
        if not department:
            department = Department(college_id=college.id, name="Computer Science", code="CSE")
            db.add(department); db.flush()
        klass = one(db, Class, Class.department_id == department.id, Class.name == "B.Tech CSE", Class.section == "A")
        if not klass:
            klass = Class(college_id=college.id, department_id=department.id, name="B.Tech CSE", academic_year="2026-27", section="A")
            db.add(klass); db.flush()
        if not one(db, StaffDepartment, StaffDepartment.user_id == staff.id, StaffDepartment.department_id == department.id):
            db.add(StaffDepartment(user_id=staff.id, department_id=department.id, is_active=True))
        if not one(db, StaffClass, StaffClass.staff_id == staff.id, StaffClass.class_id == klass.id):
            db.add(StaffClass(staff_id=staff.id, class_id=klass.id, is_incharge=True))

        student = one(db, Student, Student.user_id == student_user.id)
        if not student:
            student = Student(college_id=college.id, user_id=student_user.id, profile_id=student_user.profile_id, application_number="APP-DEMO-001", register_number="REG-DEMO-001", stage="enrolled", tenth_mark=Decimal("92"), twelfth_mark=Decimal("89"))
            db.add(student); db.flush()
        if not one(db, StudentClass, StudentClass.student_id == student.id, StudentClass.class_id == klass.id):
            db.add(StudentClass(student_id=student.id, class_id=klass.id, academic_year="2026-27"))

        math = one(db, Topic, Topic.college_id == college.id, Topic.slug == "mathematics")
        if not math:
            math = Topic(college_id=college.id, name="Mathematics", slug="mathematics", order_index=1)
            db.add(math); db.flush()
        algebra = one(db, Topic, Topic.college_id == college.id, Topic.slug == "algebra")
        if not algebra:
            algebra = Topic(college_id=college.id, name="Algebra", slug="algebra", parent_id=math.id, order_index=1)
            db.add(algebra); db.flush()
        question = one(db, Question, Question.college_id == college.id, Question.text == "What is 2 + 2?")
        if not question:
            question = Question(college_id=college.id, topic_id=algebra.id, text="What is 2 + 2?", question_type="single_choice", options=["3", "4", "5", "6"], correct_answer="4", explanation="Two plus two equals four.", difficulty="easy", marks=1, is_active=True, created_by=staff.id)
            db.add(question); db.flush()

        quiz = one(db, Quiz, Quiz.college_id == college.id, Quiz.name == "CSE Maths Quiz")
        if not quiz:
            now = datetime.now(timezone.utc)
            quiz = Quiz(college_id=college.id, name="CSE Maths Quiz", description="Demo class quiz", quiz_type="class", subject="Mathematics", schedule_start=now - timedelta(days=1), schedule_end=now + timedelta(days=30), duration_minutes=20, created_by=staff.id, status="published")
            db.add(quiz); db.flush()
        if not one(db, QuizQuestion, QuizQuestion.quiz_id == quiz.id, QuizQuestion.question_id == question.id):
            db.add(QuizQuestion(quiz_id=quiz.id, question_id=question.id, order_index=1, marks=1))
        if not one(db, QuizClassTarget, QuizClassTarget.quiz_id == quiz.id, QuizClassTarget.class_id == klass.id):
            db.add(QuizClassTarget(quiz_id=quiz.id, class_id=klass.id, assigned_by=staff.id))

        exam_type = one(db, ExamType, ExamType.name == "Engineering Entrance")
        if not exam_type:
            exam_type = ExamType(name="Engineering Entrance", description="Demo entrance examination")
            db.add(exam_type); db.flush()
        exam = one(db, Exam, Exam.college_id == college.id, Exam.name == "DEMO Engineering Entrance 2026")
        if not exam:
            now = datetime.now(timezone.utc)
            exam = Exam(college_id=college.id, name="DEMO Engineering Entrance 2026", description="A free, seeded entrance exam.", exam_type_id=exam_type.id, starts_at=now + timedelta(days=14), ends_at=now + timedelta(days=14, hours=2), duration_minutes=120, fee=Decimal("0"), fee_currency="INR", status="published", created_by=admin.id)
            db.add(exam); db.flush()
        if not one(db, ExamQuiz, ExamQuiz.exam_id == exam.id, ExamQuiz.quiz_id == quiz.id): db.add(ExamQuiz(exam_id=exam.id, quiz_id=quiz.id, order_index=1, weight=Decimal("1")))
        if not one(db, ExamTopicWeight, ExamTopicWeight.exam_id == exam.id, ExamTopicWeight.topic_id == algebra.id): db.add(ExamTopicWeight(exam_id=exam.id, topic_id=algebra.id, question_count=1, weight=Decimal("1")))
        slot = one(db, ExamSlot, ExamSlot.college_id == college.id, ExamSlot.name == "Morning Batch")
        if not slot:
            now = datetime.now(timezone.utc)
            slot = ExamSlot(college_id=college.id, name="Morning Batch", starts_at=now + timedelta(days=14), ends_at=now + timedelta(days=14, hours=3), max_capacity=100, status="open")
            db.add(slot); db.flush()
        if not one(db, ExamRegistration, ExamRegistration.exam_id == exam.id, ExamRegistration.student_id == student.id):
            db.add(ExamRegistration(college_id=college.id, student_id=student.id, exam_id=exam.id, slot_id=slot.id, registration_number="REG-DEMO-ENT-001", status="confirmed", registered_at=datetime.now(timezone.utc), confirmed_at=datetime.now(timezone.utc)))

        problem = one(db, Problem, Problem.college_id == college.id, Problem.slug == "sum-two-numbers")
        if not problem:
            problem = Problem(college_id=college.id, uuid=str(uuid4()), title="Sum Two Numbers", slug="sum-two-numbers", description="Read two integers and print their sum.", difficulty="easy", time_limit_ms=1000, memory_limit_kb=65536, allowed_languages=["python", "javascript"], default_language="python", is_active=True, created_by=staff.id)
            db.add(problem); db.flush(); db.add_all([ProblemTopic(problem_id=problem.id, topic_id=algebra.id), TestCase(problem_id=problem.id, input="2 3", expected_output="5", is_hidden=False, order_index=1, points=1)])
        if not one(db, TrainingAssignment, TrainingAssignment.problem_id == problem.id): db.add(TrainingAssignment(college_id=college.id, problem_id=problem.id, title="Prompt-to-code: sum numbers", instructions="Write a precise prompt, then debug the generated solution.", max_debug_submissions=3, time_limit_minutes=30, created_by=staff.id))
        db.commit()
        print("Seed complete. Login with superadmin/admin/staff/student, password: Demo@12345")
    except Exception:
        db.rollback(); raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
