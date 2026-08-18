import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DB = os.getenv("DB")

    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-env")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Comma-separated list of origins the frontend is served from, e.g.
    # "http://localhost:5173,https://app.example.com". No frontend can call
    # this API cross-origin until this is set to something real.
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]

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

    # Anthropic API (training module: generates code from a student's
    # one-shot prompt). Update ANTHROPIC_MODEL as newer models ship.
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    # Which backend utils/llm.py uses for the training module's code
    # generation: "ollama" (local, free — default) or "anthropic" (needs
    # ANTHROPIC_API_KEY, paid). Switch to "anthropic" once you have credits;
    # no code changes needed.
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
