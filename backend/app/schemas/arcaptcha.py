import enum

from pydantic import BaseModel


class CaptchaStatus(enum.StrEnum):
    PENDING = "pending"
    SOLVED = "solved"
    NOT_SOLVED = "not_solved"
    VERIFICATION_FAILED = "verification_failed"
    UNKNOWN = "unknown"


class ArcaptchaMetadata(BaseModel):
    challenge_id: str | None = None
    captcha_status: CaptchaStatus = CaptchaStatus.PENDING
