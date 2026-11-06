import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Run, RunEvent, RunStatus


async def claim_next_run(
    worker_id: str = "worker-1",
    target_run_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    async with SessionLocal() as session:
        query = select(Run).where(Run.status == RunStatus.PENDING)
        if target_run_id:
            query = query.where(Run.id == target_run_id)
        else:
            query = query.order_by(Run.created_at.asc())

        stmt = query.limit(1).with_for_update(skip_locked=True)
        result = await session.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return None

        claimed_id = run.id
        now = datetime.now(UTC)

        run.status = RunStatus.RUNNING
        run.started_at = now

        session.add(
            RunEvent(
                run_id=claimed_id,
                event_type="claimed",
                message=f"Claimed by {worker_id}",
                created_at=now,
            )
        )
        await session.commit()
        return claimed_id


async def recover_stale_runs(worker_id: str) -> int:
    async with SessionLocal() as session:
        stmt = select(Run).where(Run.status == RunStatus.RUNNING)
        result = await session.execute(stmt)
        stale_runs = result.scalars().all()

        if not stale_runs:
            return 0

        now = datetime.now(UTC)
        count = len(stale_runs)

        for run in stale_runs:
            run.status = RunStatus.FAILED
            run.finished_at = now
            run.error_message = (
                f"Execution interrupted: {worker_id} restarted unexpectedly"
            )
            session.add(
                RunEvent(
                    run_id=run.id,
                    event_type="interrupted",
                    message="Process interrupted by worker restart",
                    created_at=now,
                )
            )

        await session.commit()
        return count
