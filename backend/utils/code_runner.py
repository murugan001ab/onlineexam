"""Grades a Submission by running the user's code against its problem's
test cases via a Piston-compatible execution API
(https://github.com/engineer-man/piston).

NOTE: the public emkc.org Piston API now requires an authorization key
(as of Feb 2026) and is rate-limited to 5 req/s even with one. Point
PISTON_BASE_URL (core.settings) at a self-hosted instance for anything
beyond light testing:
    docker-compose up -d api   # from the piston repo
"""

import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.database import SessionLocal
from core.settings import Settings
from models.problem import Problem, Submission

# Maps our Submission.language / Problem.allowed_languages values to a
# Piston runtime language + source filename. Keep in sync with whatever
# languages problems are allowed to declare.
LANGUAGE_CONFIG: dict[str, dict[str, str]] = {
    "python3": {"piston_language": "python", "filename": "main.py"},
    "java": {"piston_language": "java", "filename": "Main.java"},
    "c": {"piston_language": "c", "filename": "main.c"},
}

_runtime_versions_cache: dict[str, str] = {}


async def _resolve_version(client: httpx.AsyncClient, piston_language: str) -> str:
    if piston_language not in _runtime_versions_cache:
        resp = await client.get("/api/v2/piston/runtimes")
        resp.raise_for_status()
        for runtime in resp.json():
            _runtime_versions_cache[runtime["language"]] = runtime["version"]
    return _runtime_versions_cache.get(piston_language, "*")


async def _run_one(
    client: httpx.AsyncClient,
    *,
    piston_language: str,
    version: str,
    filename: str,
    code: str,
    stdin: str,
    time_limit_ms: int,
) -> dict[str, Any]:
    payload = {
        "language": piston_language,
        "version": version,
        "files": [{"name": filename, "content": code}],
        "stdin": stdin,
        "run_timeout": time_limit_ms,
    }
    resp = await client.post("/api/v2/piston/execute", json=payload)
    resp.raise_for_status()
    return resp.json()


async def grade_submission(submission_id: int) -> None:
    """Runs as a FastAPI background task with its own DB session — the
    request's session is already closed by the time this executes."""
    db: Session = SessionLocal()
    try:
        submission = db.get(Submission, submission_id)
        if submission is None:
            return

        problem = db.execute(
            select(Problem)
            .where(Problem.id == submission.problem_id)
            .options(selectinload(Problem.test_cases))
        ).scalar_one_or_none()
        if problem is None:
            submission.status = "error"
            db.commit()
            return

        config = LANGUAGE_CONFIG.get(submission.language)
        if config is None:
            submission.status = "error"
            submission.results = {"error": f"unsupported language '{submission.language}'"}
            db.commit()
            return

        submission.status = "running"
        db.commit()

        test_cases = sorted(problem.test_cases, key=lambda t: (t.order_index or 0))
        max_score = sum(tc.points or 0 for tc in test_cases)
        time_limit_ms = problem.time_limit_ms or 5000

        results: list[dict[str, Any]] = []
        total_score = 0
        overall_status = "accepted"
        slowest_ms = 0

        headers = {}
        if Settings.PISTON_API_KEY:
            headers["Authorization"] = Settings.PISTON_API_KEY

        async with httpx.AsyncClient(
            base_url=Settings.PISTON_BASE_URL, headers=headers, timeout=30.0
        ) as client:
            try:
                version = await _resolve_version(client, config["piston_language"])
            except httpx.HTTPError:
                submission.status = "error"
                submission.results = {"error": "execution service unavailable"}
                db.commit()
                return

            for tc in test_cases:
                points = tc.points or 0
                try:
                    raw = await _run_one(
                        client,
                        piston_language=config["piston_language"],
                        version=version,
                        filename=config["filename"],
                        code=submission.code,
                        stdin=tc.input or "",
                        time_limit_ms=time_limit_ms,
                    )
                except httpx.HTTPError:
                    results.append(
                        {"test_case_id": tc.id, "is_hidden": tc.is_hidden, "passed": False}
                    )
                    overall_status = "error"
                    break

                compile_stage = raw.get("compile")
                run_stage = raw.get("run") or {}

                if compile_stage and compile_stage.get("code") not in (0, None):
                    entry: dict[str, Any] = {
                        "test_case_id": tc.id,
                        "is_hidden": tc.is_hidden,
                        "passed": False,
                    }
                    if not tc.is_hidden:
                        entry["stderr"] = compile_stage.get("stderr")
                    results.append(entry)
                    overall_status = "compilation_error"
                    break  # same code fails to compile for every case

                elapsed_ms = int(run_stage.get("time", 0) * 1000) if run_stage.get("time") else 0
                slowest_ms = max(slowest_ms, elapsed_ms)

                stdout = (run_stage.get("stdout") or "").strip()
                expected = (tc.expected_output or "").strip()
                exit_code = run_stage.get("code")
                passed = exit_code == 0 and stdout == expected
                if passed:
                    total_score += points

                entry = {
                    "test_case_id": tc.id,
                    "is_hidden": tc.is_hidden,
                    "passed": passed,
                    "time_ms": elapsed_ms,
                }
                if not tc.is_hidden:
                    entry["stdout"] = stdout
                    entry["expected"] = expected
                    if run_stage.get("stderr"):
                        entry["stderr"] = run_stage["stderr"]
                results.append(entry)

                if not passed and overall_status == "accepted":
                    if run_stage.get("signal") in ("SIGKILL", "SIGTERM"):
                        overall_status = "timeout"
                    elif exit_code not in (0, None):
                        overall_status = "runtime_error"
                    else:
                        overall_status = "wrong_answer"

        submission.status = overall_status
        submission.score = total_score
        submission.max_score = max_score
        submission.runtime_ms = slowest_ms
        submission.results = results
        db.commit()
    finally:
        db.close()
