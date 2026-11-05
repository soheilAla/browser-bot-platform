import pytest
from pydantic import ValidationError

from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.bots.registry import registry
from app.core.db import SessionLocal
from app.execution.runner import execute_run
from app.models import BrowserMode, Run, RunStatus
from app.schemas.arcaptcha import ArcaptchaMetadata, CaptchaStatus


def test_arcaptcha_metadata_validation() -> None:
    meta = ArcaptchaMetadata()
    assert meta.challenge_id is None
    assert meta.captcha_status == CaptchaStatus.PENDING
    assert meta.extra == {}

    valid = ArcaptchaMetadata(
        challenge_id="test-challenge-123",
        captcha_status=CaptchaStatus.SOLVED,
        extra={"ip": "127.0.0.1", "attempts": 1},
    )
    assert valid.challenge_id == "test-challenge-123"
    assert valid.captcha_status == CaptchaStatus.SOLVED
    assert valid.extra["attempts"] == 1

    with pytest.raises(ValidationError):
        ArcaptchaMetadata(captcha_status="invalid_status")  # type: ignore


class DummyMergeBot(BaseBot):
    bot_id = "dummy_merge_bot"
    name = "Dummy Merge Bot"

    def run(self, context: BotContext) -> BotResult:
        # partial update
        context.update_metadata({"key_a": "value_a", "counter": 1})
        context.log("step_1", "Updated key_a")

        # secondary partial update (must NOT overwrite key_a)
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
