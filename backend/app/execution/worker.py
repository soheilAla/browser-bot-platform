import asyncio
import logging
import signal
import uuid

from app.execution.queue import claim_next_run, recover_stale_runs
from app.execution.runner import execute_run

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [worker] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("worker")


class BotWorker:
    def __init__(
        self, worker_id: str | None = None, poll_interval: float = 1.0
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:6]}"
        self.poll_interval = poll_interval
        self._running = False

    def stop(self) -> None:
        logger.info("Shutdown signal received. Stopping worker...")
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info(f"Starting {self.worker_id} (poll interval: {self.poll_interval}s)")

        recovered = await recover_stale_runs(self.worker_id)
        if recovered:
            logger.warning(f"Startup sweep recovered {recovered} interrupted run(s)")

        while self._running:
            try:
                run_id = await claim_next_run(self.worker_id)
                if run_id:
                    logger.info(f"Claimed run {run_id}. Executing bot workflow...")
                    await execute_run(run_id)
                    logger.info(f"Finished processing run {run_id}")
                else:
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

        logger.info(f"{self.worker_id} stopped cleanly.")


def main() -> None:
    worker = BotWorker()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loop
            pass

    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        worker.stop()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
