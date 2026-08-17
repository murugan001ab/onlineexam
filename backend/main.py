from fastapi import FastAPI

from routers import admin, auth, organization, problems, submissions, topics

app = FastAPI(title="Online Exam API")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(organization.router)
app.include_router(topics.router)
app.include_router(problems.router)
app.include_router(submissions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
