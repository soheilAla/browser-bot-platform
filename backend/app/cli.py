import argparse
import asyncio
import sys

from sqlalchemy import select

from app.bots.registry import registry
from app.core.db import SessionLocal
from app.execution.runner import execute_run
from app.models import BrowserMode, Run, RunEvent, RunStatus


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a bot on the Browser Bot Platform"
    )
    parser.add_argument(
        "--bot",
        default="arcaptcha",
        choices=[b["bot_id"] for b in registry.list()],
        help="Bot ID to execute (default: arcaptcha)",
    )
    parser.add_argument(
        "--mode",
        default="headful",
        choices=["headful", "headless"],
        help="Browser mode: headful or headless (default: headful)",
    )
    args = parser.parse_args()

    browser_mode = (
        BrowserMode.HEADFUL if args.mode == "headful" else BrowserMode.HEADLESS
    )

    print("=" * 60)
    print(f"🚀 Initializing run for bot '{args.bot}' in '{browser_mode}' mode...")
    print("=" * 60)

    async with SessionLocal() as session:
        run = Run(
            bot_id=args.bot,
            browser_mode=browser_mode,
            status=RunStatus.PENDING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    print(f"📝 Created Run record in database: {run_id}")
    if browser_mode == BrowserMode.HEADFUL:
        print("🖥️  Watch live in noVNC: http://localhost:7900/?autoconnect=1")
    print("-" * 60)

    try:
        await execute_run(run_id)
    except Exception as e:
        print(f"❌ Execution failed: {e}", file=sys.stderr)
        return

    async with SessionLocal() as session:
        r = await session.get(Run, run_id)
        if not r:
            return

        print("\n" + "=" * 60)
        print("🏁 RUN FINISHED REPORT")
        print("=" * 60)
        print(f"Run ID:         {r.id}")
        print(f"Bot:            {r.bot_id}")
        print(f"Mode:           {r.browser_mode}")
        print(f"Status:         {r.status.upper()}")
        print(f"Metadata:       {r.bot_metadata or {}}")
        print(f"Started At:     {r.started_at}")
        print(f"Finished At:    {r.finished_at}")
        if r.error_message:
            print(f"Message:        {r.error_message}")

        events_res = await session.execute(
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at)
        )
        events = events_res.scalars().all()
        print("\n📜 Persisted Run Events:")
        for ev in events:
            time_str = ev.created_at.strftime("%H:%M:%S")
            print(f"  [{time_str}] [{ev.event_type}] {ev.message}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
