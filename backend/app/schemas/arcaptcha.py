import enum
from typing import Any

from pydantic import BaseModel, Field


class CaptchaStatus(enum.StrEnum):
    PENDING = "pending"
    SOLVED = "solved"
    NOT_SOLVED = "not_solved"
    VERIFICATION_FAILED = "verification_failed"


class ArcaptchaMetadata(BaseModel):
    challenge_id: str | None = None
    captcha_status: CaptchaStatus = CaptchaStatus.PENDING
    extra: dict[str, Any] = Field(default_factory=dict)
