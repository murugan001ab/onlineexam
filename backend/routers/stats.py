from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.attempt import ExamAttempt
from models.auth import User
from models.entrance import ExamRegistration
from models.exam import Exam
from models.student import Student
from schemas.stats import ExamStatsOut, RankedAttemptOut, ScoreBandOut

router = APIRouter(prefix="/admin", tags=["exam-stats"])

# (label, min_percent_inclusive, max_percent_inclusive)
_BANDS = [
    ("90-100", 90.0, 100.0),
    ("80-89", 80.0, 89.999999),
    ("70-79", 70.0, 79.999999),
    ("60-69", 60.0, 69.999999),
    ("50-59", 50.0, 59.999999),
    ("40-49", 40.0, 49.999999),
    ("10-39", 10.0, 39.999999),
    ("0-9", 0.0, 9.999999),
]


@router.get("/exams/{exam_id}/stats", response_model=ExamStatsOut)
def get_exam_stats(exam_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    """Post-exam result breakdown: how many candidates fell into each
    percentage band, plus a full top-to-bottom ranking. Percentage is
    computed per-attempt from score/max_score so this stays correct
    regardless of how many questions/marks the exam actually had."""
    exam = db.execute(select(Exam).where(Exam.id == exam_id, Exam.college_id == user.college_id)).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")

    total_registered = db.execute(
        select(ExamRegistration).where(
            ExamRegistration.exam_id == exam.id,
            ExamRegistration.status.in_(("confirmed", "completed")),
        )
    ).scalars().all()

    attempts = db.execute(
        select(ExamAttempt)
        .where(ExamAttempt.exam_id == exam.id)
        .options(
            selectinload(ExamAttempt.student).selectinload(Student.profile),
        )
    ).scalars().all()

    total_attempted = len(attempts)
    submitted = [a for a in attempts if a.status in ("submitted", "expired") and a.score is not None and a.max_score]
    disqualified = [a for a in attempts if a.status == "disqualified"]

    percentages: list[float] = []
    ranking: list[RankedAttemptOut] = []
    for a in submitted:
        pct = float(a.score) / float(a.max_score) * 100 if a.max_score else 0.0
        percentages.append(pct)
        student = a.student
        profile = student.profile if student else None
        ranking.append(
            RankedAttemptOut(
                rank=0,  # filled in after sort
                attempt_id=a.id,
                student_id=a.student_id,
                student_name=profile.name if profile else None,
                register_number=student.register_number if student else None,
                application_number=student.application_number if student else None,
                score=a.score,
                max_score=a.max_score,
                percentage=round(pct, 2),
                submitted_at=a.submitted_at.isoformat() if a.submitted_at else None,
            )
        )

    ranking.sort(key=lambda r: (r.percentage or 0.0), reverse=True)
    for i, r in enumerate(ranking, start=1):
        r.rank = i

    bands = [
        ScoreBandOut(
            label=label,
            min_percent=lo,
            max_percent=hi,
            count=sum(1 for p in percentages if lo <= p <= hi),
        )
        for label, lo, hi in _BANDS
    ]

    return ExamStatsOut(
        exam_id=exam.id,
        exam_name=exam.name,
        total_registered=len(total_registered),
        total_attempted=total_attempted,
        total_submitted=len(submitted),
        total_disqualified=len(disqualified),
        average_percentage=round(sum(percentages) / len(percentages), 2) if percentages else None,
        highest_percentage=round(max(percentages), 2) if percentages else None,
        lowest_percentage=round(min(percentages), 2) if percentages else None,
        bands=bands,
        ranking=ranking,
    )
