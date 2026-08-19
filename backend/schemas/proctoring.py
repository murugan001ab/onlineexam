from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ProctoringEventType = Literal[
    "tab_switch",
    "window_blur",
    "fullscreen_exit",
    "copy",
    "paste",
    "right_click",
    "devtools",
    "face_missing",
    "multiple_faces",
]


class ProctoringEventIn(BaseModel):
    event_type: ProctoringEventType
    metadata: Optional[Any] = None
    occurred_at: Optional[datetime] = None


class ProctoringEventBatchIn(BaseModel):
    """The exam-taking page buffers events client-side and flushes them in
    small batches rather than firing one request per tab-switch, so a flaky
    connection doesn't drop proctoring signal."""

    events: list[ProctoringEventIn] = Field(min_length=1, max_length=50)


class ProctoringEventOut(BaseModel):
    # populate_by_name lets this be built two ways: from an ORM row (which
    # exposes the reserved SQLAlchemy attribute as metadata_, matched via
    # alias) or from plain keyword args using the field name "metadata"
    # (used by routers/stats.py and routers/proctoring.py directly).
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    event_type: Optional[str] = None
    metadata: Optional[Any] = Field(default=None, alias="metadata_")
    occurred_at: Optional[datetime] = None


class ProctoringSnapshotIn(BaseModel):
    image_base64: str = Field(min_length=1)


class ProctoringEventBatchOut(BaseModel):
    accepted: int
    warning_count: int
    max_warnings: int
    disqualified: bool


class ProctoringSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_url: str
    face_count: Optional[int] = None
    flagged: bool
    captured_at: Optional[datetime] = None


class ProctoringSummaryOut(BaseModel):
    """Admin-facing rollup for one attempt: counts per event type plus the
    snapshot timeline, so staff don't have to page through raw event rows."""

    attempt_id: int
    total_events: int
    event_counts: dict[str, int]
    flagged_snapshot_count: int
    disqualified: bool
    events: list[ProctoringEventOut]
    snapshots: list[ProctoringSnapshotOut]
