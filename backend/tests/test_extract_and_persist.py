import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.execution.runner import execute_run
from app.models import BrowserMode, Run, RunEvent, RunStatus


@pytest.mark.asyncio
async def test_extract_and_persist_challenge_id() -> None:
    async with SessionLocal() as session:
        run = Run(
            bot_id="arcaptcha",
            browser_mode=BrowserMode.HEADFUL,
            status=RunStatus.PENDING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    await execute_run(run_id)

    async with SessionLocal() as session:
        r = await session.get(Run, run_id)
        assert r is not None
        assert r.id == run_id
        assert r.status in [RunStatus.SUCCESS, RunStatus.BLOCKED, RunStatus.FAILED]
        assert r.started_at is not None
        assert r.finished_at is not None

        # Challenge ID must be extracted and saved in DB
        assert r.challenge_id is not None
        assert len(r.challenge_id) > 10
        print(f"\n[PERSISTED] Run ID: {r.id}")
        print(f"[PERSISTED] Challenge ID: {r.challenge_id}")
        print(f"[PERSISTED] Final Status: {r.status}")
        print(f"[PERSISTED] Message: {r.error_message}")

        # Verify events were persisted in run_events table
        events_res = await session.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at)
        )
        events = events_res.scalars().all()
        assert len(events) >= 4
        event_types = [e.event_type for e in events]
        print(f"[PERSISTED] Event types: {event_types}")

        assert "started" in event_types
        assert "challenge_extracted" in event_types
        assert "finished" in event_types
