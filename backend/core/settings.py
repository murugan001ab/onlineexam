import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB = os.getenv("DB")

    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-env")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Code execution (Piston-compatible API). The public emkc.org API now
    # requires an authorization key (as of Feb 2026) — point this at a
    # self-hosted Piston instance (github.com/engineer-man/piston) unless
    # you have one. Base URL only, no trailing /api/v2/piston.
    PISTON_BASE_URL = os.getenv("PISTON_BASE_URL", "http://localhost:2000")
    PISTON_API_KEY = os.getenv("PISTON_API_KEY", "")

    # Razorpay (entrance exam registration payments). If either is unset, the
    # payment flow falls back to a local "mock" order/verify mode so the rest
    # of the booking flow can be developed/tested without live credentials.
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

    # Minutes an ExamSlot hold stays reserved before it must be converted to
    # a registration (payment started) or it's treated as expired.
    SLOT_HOLD_MINUTES = int(os.getenv("SLOT_HOLD_MINUTES", "10"))
