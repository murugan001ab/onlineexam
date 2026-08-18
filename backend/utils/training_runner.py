"""Grades a TrainingSubmission (the debug-loop step of the one-shot prompt
training flow) against its assignment's problem test cases, then rolls the
result up into the parent TrainingAttempt.

Reuses the same Piston-calling helpers as utils/code_runner.py (which
grades the separate practice-mode Submission model) rather than duplicating
the runtime/version-resolution logic.
"""

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.database import SessionLocal
from core.settings import Settings
from models.problem import Problem
from models.training import TrainingAssignment, TrainingAttempt, TrainingSubmission
from utils.code_runner import LANGUAGE_CONFIG, _resolve_version, _run_one


async def grade_training_submission(training_submission_id: int) -> None:
    """Runs as a FastAPI background task with its own DB session."""
    db: Session = SessionLocal()
    try:
        submission = db.get(TrainingSubmission, training_submission_id)
        if submission is None:
            return

        attempt = db.execute(
            select(TrainingAttempt)
            .where(TrainingAttempt.id == submission.training_attempt_id)
            .options(selectinload(TrainingAttempt.assignment))
        ).scalar_one_or_none()
        if attempt is None:
            submission.status = "error"
            db.commit()
            return

        problem = db.execute(
            select(Problem)
            .where(Problem.id == attempt.assignment.problem_id)
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
        passed_count = 0

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
                    results.append({"test_case_id": tc.id, "is_hidden": tc.is_hidden, "passed": False})
                    overall_status = "error"
                    break

                compile_stage = raw.get("compile")
                run_stage = raw.get("run") or {}

                if compile_stage and compile_stage.get("code") not in (0, None):
                    entry: dict[str, Any] = {"test_case_id": tc.id, "is_hidden": tc.is_hidden, "passed": False}
                    if not tc.is_hidden:
                        entry["stderr"] = compile_stage.get("stderr")
                    results.append(entry)
                    overall_status = "compilation_error"
                    break

                elapsed_ms = int(run_stage.get("time", 0) * 1000) if run_stage.get("time") else 0
                slowest_ms = max(slowest_ms, elapsed_ms)

                stdout = (run_stage.get("stdout") or "").strip()
                expected = (tc.expected_output or "").strip()
                exit_code = run_stage.get("code")
                passed = exit_code == 0 and stdout == expected
                if passed:
                    total_score += points
                    passed_count += 1

                entry = {"test_case_id": tc.id, "is_hidden": tc.is_hidden, "passed": passed, "time_ms": elapsed_ms}
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
        submission.passed_test_cases = passed_count
        submission.total_test_cases = len(test_cases)
        submission.results = results
        db.commit()

        # ---- roll up onto the attempt: keep the *best* attempt across all
        # debug submissions, and close out the attempt once the student has
        # either passed everything or run out of debug submissions.
        all_submissions = db.execute(
            select(TrainingSubmission).where(TrainingSubmission.training_attempt_id == attempt.id)
        ).scalars().all()

        best = max(
            all_submissions,
            key=lambda s: ((s.score or 0) / s.max_score if s.max_score else 0),
        )
        best_pass_rate = round((best.score or 0) / best.max_score * 100, 2) if best.max_score else 0

        attempt.test_pass_rate = best_pass_rate
        attempt.final_score = best.score

        assignment: TrainingAssignment = attempt.assignment
        out_of_attempts = (
            assignment.max_debug_submissions is not None
            and attempt.debug_submission_count >= assignment.max_debug_submissions
        )
        if best_pass_rate >= 100 or out_of_attempts:
            attempt.status = "completed"
            attempt.completed_at = datetime.now(timezone.utc)
        else:
            attempt.status = "debugging"
        db.commit()
    finally:
        db.close()
