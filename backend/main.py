from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import Settings
from routers import (
    admin,
    attempt,
    auth,
    exam,
    organization,
    problems,
    questions,
    quiz,
    quiz_attempt,
    registration,
    students,
    submissions,
    topics,
    training,
)

app = FastAPI(title="Online Exam API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(organization.router)
app.include_router(students.router)
app.include_router(topics.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(questions.router)
app.include_router(quiz.router)
app.include_router(quiz_attempt.student_router)
app.include_router(quiz_attempt.admin_router)
app.include_router(exam.router)
app.include_router(registration.student_router)
app.include_router(registration.admin_router)
app.include_router(training.admin_router)
app.include_router(training.student_router)
app.include_router(attempt.student_router)
app.include_router(attempt.admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}
