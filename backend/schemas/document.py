from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

DocType = Literal["tenth_marksheet", "twelfth_marksheet", "diploma_marksheet", "age_proof", "photo"]
DocStatus = Literal["pending", "verified", "rejected"]


class StudentDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    doc_type: DocType
    issued_place: Optional[str] = None
    issuing_board: Optional[str] = None
    file_url: str
    original_filename: Optional[str] = None
    status: DocStatus
    remarks: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class StudentDocumentReview(BaseModel):
    status: Literal["verified", "rejected"]
    remarks: Optional[str] = Field(default=None, max_length=1000)
