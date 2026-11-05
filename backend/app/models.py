import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class RunStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CHALLENGE = "awaiting_challenge"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class BrowserMode(enum.StrEnum):
    HEADLESS = "headless"
    HEADFUL = "headful"


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (Index("ix_runs_status_created_at", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bot_id: Mapped[str] = mapped_column(String(100))
    browser_mode: Mapped[BrowserMode] = mapped_column(
        Enum(BrowserMode, native_enum=False)
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False),
        default=RunStatus.PENDING,
    )
    bot_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default="{}", default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["RunEvent"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunEvent.created_at",
    )


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (Index("ix_run_events_run_id_created_at", "run_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["Run"] = relationship(back_populates="events")
