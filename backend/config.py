import os

from dotenv import load_dotenv

load_dotenv()


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


class Config:
    VISION_PROVIDER = os.getenv("VISION_PROVIDER", "gemini")  # gemini | mock
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    AI_TIMEOUT_SECONDS = _int("AI_TIMEOUT_SECONDS", 45)
    # Vercel functions reject request bodies over ~4.5 MB, so stay below that.
    MAX_IMAGE_BYTES = _int("MAX_IMAGE_BYTES", 4 * 1024 * 1024)
    MAX_CONTENT_LENGTH = MAX_IMAGE_BYTES + 512 * 1024  # room for form fields
    MAX_TEXT_CHARS = _int("MAX_TEXT_CHARS", 10000)
    RATE_LIMIT_PER_MIN = _int("RATE_LIMIT_PER_MIN", 10)
    TRUST_PROXY = os.getenv("TRUST_PROXY", "") == "1"  # set to 1 behind Vercel/nginx
