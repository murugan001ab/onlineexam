"""Small SMTP adapter used for exam invitation mail.

When SMTP_HOST is empty (local development), messages are logged instead of
raising so payment/registration remains successful.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from core.settings import Settings

log = logging.getLogger(__name__)


def send_otp_email(*, to_email: str, code: str, expires_in_minutes: int) -> bool:
    subject = "Your verification code"
    text = f"""Your one-time verification code is: {code}

This code expires in {expires_in_minutes} minutes. If you did not request this, you can ignore this email.
"""
    if not Settings.SMTP_HOST:
        log.warning("SMTP is not configured; OTP email to %s would read:\n%s", to_email, text)
        return False
    msg = EmailMessage(); msg["Subject"] = subject; msg["From"] = Settings.SMTP_FROM; msg["To"] = to_email; msg.set_content(text)
    try:
        if Settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(Settings.SMTP_HOST, Settings.SMTP_PORT, context=ssl.create_default_context()) as smtp:
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        return True
    except Exception:
        log.exception("Could not send OTP email to %s", to_email)
        return False


def send_registration_confirmation(*, to_email: str | None, student_name: str, exam_name: str,
                                    registration_number: str, exam_starts_at: object,
                                    fee_paid: bool) -> bool:
    if not to_email:
        log.warning("Registration confirmation not sent: student has no email address")
        return False
    subject = f"Registration confirmed — {exam_name}"
    payment_line = "Your payment has been received." if fee_paid else "This exam has no registration fee."
    text = f"""Hello {student_name},

Your registration for {exam_name} is confirmed.
Registration number: {registration_number}
Exam time: {exam_starts_at}
{payment_line}

You will receive a separate email with your exam login details closer to the exam date,
and another reminder shortly before the exam starts. Keep your registration number handy.
"""
    if not Settings.SMTP_HOST:
        log.warning("SMTP is not configured; registration confirmation for %s would be sent to %s\n%s", exam_name, to_email, text)
        return False
    msg = EmailMessage(); msg["Subject"] = subject; msg["From"] = Settings.SMTP_FROM; msg["To"] = to_email; msg.set_content(text)
    try:
        if Settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(Settings.SMTP_HOST, Settings.SMTP_PORT, context=ssl.create_default_context()) as smtp:
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        return True
    except Exception:
        log.exception("Could not send registration confirmation to %s", to_email)
        return False


def send_exam_reminder(*, to_email: str | None, student_name: str, exam_name: str,
                        exam_starts_at: object, registration_number: str,
                        login_url: str) -> bool:
    if not to_email:
        log.warning("Exam reminder not sent: student has no email address")
        return False
    subject = f"Reminder: {exam_name} starts soon"
    text = f"""Hello {student_name},

This is a reminder that {exam_name} is coming up.
Exam time: {exam_starts_at}
Registration number: {registration_number}

Log in a few minutes early at:
{login_url}

Before the exam: use a laptop/desktop with a working camera, close every other tab and
application, and stay on a stable internet connection — the exam runs in a monitored
fullscreen window and will flag tab switches or a lost camera feed.
"""
    if not Settings.SMTP_HOST:
        log.warning("SMTP is not configured; exam reminder for %s would be sent to %s\n%s", exam_name, to_email, text)
        return False
    msg = EmailMessage(); msg["Subject"] = subject; msg["From"] = Settings.SMTP_FROM; msg["To"] = to_email; msg.set_content(text)
    try:
        if Settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(Settings.SMTP_HOST, Settings.SMTP_PORT, context=ssl.create_default_context()) as smtp:
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        return True
    except Exception:
        log.exception("Could not send exam reminder to %s", to_email)
        return False


def send_exam_invitation(*, to_email: str | None, student_name: str, exam_name: str,
                         exam_starts_at: object, invitation_url: str, expires_at: object) -> bool:
    if not to_email:
        log.warning("Exam invitation not sent: student has no email address")
        return False
    subject = f"Your exam invitation — {exam_name}"
    text = f"""Hello {student_name},

Your registration for {exam_name} is confirmed.
Exam time: {exam_starts_at}

Open this secure invitation link to set your password and access the exam:
{invitation_url}

This link expires at {expires_at}. If you did not request this, contact your college.
"""
    if not Settings.SMTP_HOST:
        log.warning("SMTP is not configured; invitation for %s would be sent to %s\n%s", exam_name, to_email, text)
        return False
    msg = EmailMessage(); msg["Subject"] = subject; msg["From"] = Settings.SMTP_FROM; msg["To"] = to_email; msg.set_content(text)
    try:
        if Settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(Settings.SMTP_HOST, Settings.SMTP_PORT, context=ssl.create_default_context()) as smtp:
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if Settings.SMTP_USERNAME: smtp.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        return True
    except Exception:
        log.exception("Could not send exam invitation to %s", to_email)
        return False
