from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ScoreBandOut(BaseModel):
    """One percentage bucket, e.g. '90-100', with how many submitted
    attempts landed in it."""

    label: str
    min_percent: float
    max_percent: float
    count: int


class RankedAttemptOut(BaseModel):
    rank: int
    attempt_id: int
    student_id: int
    student_name: Optional[str] = None
    register_number: Optional[str] = None
    application_number: Optional[str] = None
    score: Optional[Decimal] = None
    max_score: Optional[Decimal] = None
    percentage: Optional[float] = None
    submitted_at: Optional[str] = None


class ExamStatsOut(BaseModel):
    exam_id: int
    exam_name: str
    total_registered: int
    total_attempted: int
    total_submitted: int
    total_disqualified: int
    average_percentage: Optional[float] = None
    highest_percentage: Optional[float] = None
    lowest_percentage: Optional[float] = None
    bands: list[ScoreBandOut]
    ranking: list[RankedAttemptOut]
