from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.deps import STAFF_ROLES, DbSession, require_roles
from models.auth import User
from models.document import StudentDocument
from models.student import Student
from schemas.document import DocType, StudentDocumentOut, StudentDocumentReview
from utils.storage import file_url, save_upload

student_router = APIRouter(prefix="/entrance/documents", tags=["student-documents"])
admin_router = APIRouter(prefix="/admin/students", tags=["student-documents"])

RequireStudent = Depends(require_roles("student"))


def _get_student_or_404(db: DbSession, user: User) -> Student:
    student = db.execute(select(Student).where(Student.user_id == user.id)).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return student


def _serialize(doc: StudentDocument) -> StudentDocumentOut:
    return StudentDocumentOut(
        id=doc.id,
        student_id=doc.student_id,
        doc_type=doc.doc_type,
        issued_place=doc.issued_place,
        issuing_board=doc.issuing_board,
        file_url=file_url(doc.file_path),
        original_filename=doc.original_filename,
        status=doc.status,
        remarks=doc.remarks,
        reviewed_by=doc.reviewed_by,
        reviewed_at=doc.reviewed_at,
        created_at=doc.created_at,
    )


# ==================================================================
# Student-facing: upload proof documents during registration
# ==================================================================

@student_router.post("", response_model=StudentDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DbSession,
    user: User = RequireStudent,
    doc_type: DocType = Form(...),
    issued_place: Optional[str] = Form(None),
    issuing_board: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """Re-uploading the same doc_type replaces the previous file and resets
    it to 'pending' — students correcting a rejected document don't need a
    separate 'resubmit' endpoint."""
    student = _get_student_or_404(db, user)
    relative_path, original_filename, content_type = await save_upload(file, subdir=f"documents/{student.id}")

    existing = db.execute(
        select(StudentDocument).where(StudentDocument.student_id == student.id, StudentDocument.doc_type == doc_type)
    ).scalar_one_or_none()
    if existing is not None:
        existing.issued_place = issued_place
        existing.issuing_board = issuing_board
        existing.file_path = relative_path
        existing.original_filename = original_filename
        existing.content_type = content_type
        existing.status = "pending"
        existing.remarks = None
        existing.reviewed_by = None
        existing.reviewed_at = None
        doc = existing
    else:
        doc = StudentDocument(
            college_id=student.college_id,
            student_id=student.id,
            doc_type=doc_type,
            issued_place=issued_place,
            issuing_board=issuing_board,
            file_path=relative_path,
            original_filename=original_filename,
            content_type=content_type,
            status="pending",
        )
        db.add(doc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Could not save this document — try again")
    db.refresh(doc)
    return _serialize(doc)


@student_router.get("", response_model=list[StudentDocumentOut])
def list_my_documents(db: DbSession, user: User = RequireStudent):
    student = _get_student_or_404(db, user)
    docs = db.execute(
        select(StudentDocument).where(StudentDocument.student_id == student.id).order_by(StudentDocument.doc_type)
    ).scalars().all()
    return [_serialize(d) for d in docs]


# ==================================================================
# Admin/staff: review uploaded documents
# ==================================================================

@admin_router.get("/{student_id}/documents", response_model=list[StudentDocumentOut])
def list_student_documents(student_id: int, db: DbSession, user: User = Depends(require_roles(*STAFF_ROLES))):
    student = db.execute(
        select(Student).where(Student.id == student_id, Student.college_id == user.college_id)
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found")
    docs = db.execute(
        select(StudentDocument).where(StudentDocument.student_id == student.id).order_by(StudentDocument.doc_type)
    ).scalars().all()
    return [_serialize(d) for d in docs]


@admin_router.patch("/{student_id}/documents/{document_id}", response_model=StudentDocumentOut)
def review_student_document(
    student_id: int,
    document_id: int,
    payload: StudentDocumentReview,
    db: DbSession,
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    doc = db.execute(
        select(StudentDocument)
        .join(Student, Student.id == StudentDocument.student_id)
        .where(
            StudentDocument.id == document_id,
            StudentDocument.student_id == student_id,
            Student.college_id == user.college_id,
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    doc.status = payload.status
    doc.remarks = payload.remarks
    doc.reviewed_by = user.id
    doc.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    return _serialize(doc)
