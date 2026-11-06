import pytest
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.execution.queue import claim_next_run, recover_stale_runs
from app.models import BrowserMode, Run, RunEvent, RunStatus


@pytest.mark.asyncio
async def test_queue_claiming_order_and_atomicity() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(Run).where(Run.status == RunStatus.PENDING))
        await session.commit()

        run_1 = Run(
            bot_id="arcaptcha",
            browser_mode=BrowserMode.HEADFUL,
            status=RunStatus.PENDING,
            bot_metadata={"order": 1},
        )
        session.add(run_1)
        await session.commit()
        await session.refresh(run_1)
        id_1 = run_1.id

        run_2 = Run(
            bot_id="arcaptcha",
            browser_mode=BrowserMode.HEADLESS,
            status=RunStatus.PENDING,
            bot_metadata={"order": 2},
        )
        session.add(run_2)
        await session.commit()
        await session.refresh(run_2)
        id_2 = run_2.id

    claimed_1 = await claim_next_run(worker_id="test-worker-A")
    assert claimed_1 == id_1

    async with SessionLocal() as session:
        r1 = await session.get(Run, id_1)
        assert r1 is not None
        assert r1.status == RunStatus.RUNNING
        assert r1.started_at is not None

        event = (
            await session.execute(
                select(RunEvent).where(
                    RunEvent.run_id == id_1, RunEvent.event_type == "claimed"
                )
            )
        ).scalar_one_or_none()
        assert event is not None
        assert "test-worker-A" in event.message

    claimed_2 = await claim_next_run(worker_id="test-worker-B")
    assert claimed_2 == id_2


@pytest.mark.asyncio
async def test_queue_claim_empty_returns_none() -> None:
    while True:
        claimed = await claim_next_run(worker_id="drain-worker")
        if not claimed:
            break

    result = await claim_next_run(worker_id="drain-worker")
    assert result is None


@pytest.mark.asyncio
async def test_recover_stale_runs_on_worker_startup() -> None:
    async with SessionLocal() as session:
        stale_run = Run(
            bot_id="arcaptcha",
            browser_mode=BrowserMode.HEADFUL,
            status=RunStatus.RUNNING,
            bot_metadata={"crashed": True},
        )
        session.add(stale_run)
        await session.commit()
        await session.refresh(stale_run)
        stale_id = stale_run.id

    recovered_count = await recover_stale_runs(worker_id="rebooted-worker-1")
    assert recovered_count >= 1

    async with SessionLocal() as session:
        r = await session.get(Run, stale_id)
        assert r is not None
        assert r.status == RunStatus.FAILED
        assert r.finished_at is not None
        assert r.error_message is not None
        assert "interrupted" in r.error_message.lower()

        event = (
            await session.execute(
                select(RunEvent).where(
                    RunEvent.run_id == stale_id, RunEvent.event_type == "interrupted"
                )
            )
        ).scalar_one_or_none()
        assert event is not None
        assert "interrupted by worker restart" in event.message.lower()
