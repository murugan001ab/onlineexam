import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.settings import Settings
from routers import (
    admin,
    attempt,
    auth,
    documents,
    exam,
    organization,
    problems,
    proctoring,
    public,
    questions,
    quiz,
    quiz_attempt,
    registration,
    stats,
    students,
    submissions,
    topics,
    training,
)

os.makedirs(Settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Online Exam API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves applicant documents (marksheets/age proof) and proctoring snapshots
# saved by utils/storage.py. Swap for a signed-URL CDN mount once these move
# to S3/GCS — callers only depend on utils.storage.file_url().
app.mount("/uploads", StaticFiles(directory=Settings.UPLOAD_DIR, check_dir=False), name="uploads")

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(organization.router)
app.include_router(students.router)
app.include_router(topics.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(submissions.admin_router)
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
app.include_router(proctoring.student_router)
app.include_router(proctoring.admin_router)
app.include_router(documents.student_router)
app.include_router(documents.admin_router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {"status": "ok"}
