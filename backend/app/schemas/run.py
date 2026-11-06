import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import BrowserMode, RunStatus


class RunCreateRequest(BaseModel):
    bot_id: str = Field(min_length=1, max_length=100)
    browser_mode: BrowserMode = Field(default=BrowserMode.HEADFUL)


class RunResponse(BaseModel):
    id: uuid.UUID
    bot_id: str
    browser_mode: BrowserMode
    status: RunStatus
    bot_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    items: list[RunResponse]
    total: int
    limit: int
    offset: int


class RunEventResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    event_type: str = Field(max_length=100)
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
