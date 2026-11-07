import pytest
from pydantic import ValidationError
from sqlalchemy import delete

from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.bots.registry import registry
from app.core.db import SessionLocal
from app.execution.queue import claim_next_run
from app.execution.runner import execute_run
from app.models import BrowserMode, Run, RunStatus
from app.schemas.arcaptcha import ArcaptchaMetadata, CaptchaStatus


def test_arcaptcha_metadata_validation() -> None:
    meta = ArcaptchaMetadata()
    assert meta.challenge_id is None
    assert meta.captcha_status == CaptchaStatus.PENDING

    valid = ArcaptchaMetadata(
        challenge_id="test-challenge-123",
        captcha_status=CaptchaStatus.SOLVED,
    )
    assert valid.challenge_id == "test-challenge-123"
    assert valid.captcha_status == CaptchaStatus.SOLVED

    dump = valid.model_dump()
    assert dump == {
        "challenge_id": "test-challenge-123",
        "captcha_status": CaptchaStatus.SOLVED,
    }

    unknown_meta = ArcaptchaMetadata(
        challenge_id="test-challenge-456",
        captcha_status=CaptchaStatus.UNKNOWN,
    )
    assert unknown_meta.captcha_status == CaptchaStatus.UNKNOWN
    assert unknown_meta.captcha_status.value == "unknown"

    with pytest.raises(ValidationError):
        ArcaptchaMetadata(captcha_status="invalid_status")  # type: ignore


class DummyMergeBot(BaseBot):
    bot_id = "dummy_merge_bot"
    name = "Dummy Merge Bot"

    def run(self, context: BotContext) -> BotResult:
        context.update_metadata({"key_a": "value_a", "counter": 1})
        context.log("step_1", "Updated key_a")

        context.update_metadata({"key_b": "value_b", "counter": 2})
        context.log("step_2", "Updated key_b and counter")

        return BotResult(
            status=RunStatus.SUCCESS,
            message="Merge test finished",
            metadata={"key_c": "value_c"},
        )


@pytest.mark.asyncio
async def test_metadata_patch_and_merge_behavior() -> None:
    registry.register(DummyMergeBot)

    try:
        async with SessionLocal() as session:
            run = Run(
                bot_id="dummy_merge_bot",
                browser_mode=BrowserMode.HEADLESS,
                status=RunStatus.PENDING,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

        await claim_next_run(worker_id="test-worker", target_run_id=run_id)
        await execute_run(run_id)

        # Verify in DB that all metadata keys were preserved and merged correctly
        async with SessionLocal() as session:
            r = await session.get(Run, run_id)
            assert r is not None
            assert r.status == RunStatus.SUCCESS
            assert r.bot_metadata is not None

            assert r.bot_metadata.get("key_a") == "value_a"
            assert r.bot_metadata.get("key_b") == "value_b"
            assert r.bot_metadata.get("key_c") == "value_c"
            assert r.bot_metadata.get("counter") == 2
    finally:
        registry._bots.pop("dummy_merge_bot", None)
        async with SessionLocal() as session:
            await session.execute(delete(Run).where(Run.bot_id == "dummy_merge_bot"))
            await session.commit()


@pytest.mark.asyncio
async def test_runner_rejects_unclaimed_run() -> None:
    async with SessionLocal() as session:
        run = Run(
            bot_id="test_bot",
            browser_mode=BrowserMode.HEADLESS,
            status=RunStatus.PENDING,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    with pytest.raises(ValueError, match="not eligible for execution"):
        await execute_run(run_id)
