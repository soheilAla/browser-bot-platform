import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.bots.base import BotResult
from app.bots.context import BotContext
from app.bots.registry import registry
from app.core.db import SessionLocal
from app.models import Run, RunEvent, RunStatus


async def execute_run(run_id: uuid.UUID) -> Run:
    """Execute a run with lifecycle tracking and immediate DB persistence."""
    loop = asyncio.get_running_loop()

    async with SessionLocal() as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        session.add(
            RunEvent(
                run_id=run_id,
                event_type="started",
                message=(
                    f"Starting execution of bot '{run.bot_id}' "
                    f"in {run.browser_mode} mode"
                ),
            )
        )
        await session.commit()
        await session.refresh(run)

        bot_id = run.bot_id
        browser_mode = run.browser_mode

    def update_metadata(data: dict[str, Any]) -> None:
        async def _update():
            async with SessionLocal() as s:
                r = await s.get(Run, run_id)
                if r:
                    current = dict(r.bot_metadata or {})
                    current.update(data)
                    r.bot_metadata = current
                    await s.commit()

        asyncio.run_coroutine_threadsafe(_update(), loop).result()

    def log_event(event_type: str, message: str) -> None:
        async def _log():
            async with SessionLocal() as s:
                s.add(RunEvent(run_id=run_id, event_type=event_type, message=message))
                await s.commit()

        asyncio.run_coroutine_threadsafe(_log(), loop).result()

    context = BotContext(
        run_id=run_id,
        browser_mode=browser_mode,
        update_metadata=update_metadata,
        log=log_event,
    )

    bot_class = registry.get(bot_id)
    bot = bot_class(browser_mode=browser_mode)

    # Run bot in thread to keep asyncio event loop responsive
    try:
        bot_result: BotResult = await asyncio.to_thread(bot.run, context)
    except Exception as e:
        bot_result = BotResult(
            status=RunStatus.FAILED,
            message=f"Unhandled runner exception: {e}",
            metadata={"error": str(e)},
        )

    async with SessionLocal() as session:
        r = await session.get(Run, run_id)
        if r:
            r.status = bot_result.status
            if bot_result.metadata:
                current = dict(r.bot_metadata or {})
                current.update(bot_result.metadata)
                r.bot_metadata = current
            r.finished_at = datetime.now(UTC)
            r.error_message = bot_result.message

            session.add(
                RunEvent(
                    run_id=run_id,
                    event_type="finished",
                    message=(
                        f"Run finished with status '{r.status}': {bot_result.message}"
                    ),
                )
            )
            await session.commit()
            await session.refresh(r)
            return r

    raise RuntimeError(f"Run {run_id} missing during finalization")
