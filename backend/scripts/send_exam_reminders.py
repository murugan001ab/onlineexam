"""Sends the "your exam starts soon" reminder email to confirmed
registrants whose exam begins within Settings.EXAM_REMINDER_HOURS_BEFORE
hours and who haven't been reminded yet.

Run on a schedule (cron / Windows Task Scheduler), e.g. hourly:
    python -m scripts.send_exam_reminders

This complements the immediate "registration confirmed" mail sent at
registration time (routers/registration.py) and the exam-invitation mail
sent once admin generates logins (routers/registration.py: generate_invitations).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import SessionLocal
from core.settings import Settings
from models.auth import User
from models.entrance import ExamRegistration
from models.exam import Exam
from models.student import Student
from utils.email import send_exam_reminder


def main() -> None:
    db = SessionLocal()
    sent = 0
    try:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=Settings.EXAM_REMINDER_HOURS_BEFORE)

        rows = db.execute(
            select(ExamRegistration)
            .join(Exam, Exam.id == ExamRegistration.exam_id)
            .where(
                ExamRegistration.status == "confirmed",
                ExamRegistration.reminder_sent_at.is_(None),
                Exam.starts_at.is_not(None),
                Exam.starts_at > now,
                Exam.starts_at <= window_end,
            )
            .options(selectinload(ExamRegistration.exam), selectinload(ExamRegistration.student))
        ).scalars().all()

        for reg in rows:
            student = reg.student
            if student is None:
                continue
            login_url = f"{Settings.FRONTEND_URL.rstrip('/')}/login"
            if student.user_id:
                target_user = db.get(User, student.user_id)
                to_email = target_user.email if target_user and target_user.email else student.email
            else:
                to_email = student.email
            student_name = student.profile.name if student.profile else "Student"

            delivered = send_exam_reminder(
                to_email=to_email,
                student_name=student_name,
                exam_name=reg.exam.name,
                exam_starts_at=reg.exam.starts_at,
                registration_number=reg.registration_number or "",
                login_url=login_url,
            )
            # Mark as sent even in dev mode (SMTP unset -> logged, not
            # delivered) so re-running the cron doesn't spam the log forever.
            reg.reminder_sent_at = now
            if delivered:
                sent += 1
        db.commit()
        print(f"Reminder pass complete: {len(rows)} registration(s) processed, {sent} email(s) actually delivered.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
