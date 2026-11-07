import pytest

from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.bots.registry import registry
from app.core.db import engine
from app.models import RunStatus


class DummyTestBot(BaseBot):
    bot_id = "test_bot"
    name = "Test Bot"

    def run(self, context: BotContext) -> BotResult:
        context.log("test", "Dummy test bot executed")
        return BotResult(status=RunStatus.SUCCESS, message="OK")


try:
    registry.register(DummyTestBot)
except ValueError:
    pass


@pytest.fixture(autouse=True)
async def dispose_engine_after_test():
    """Dispose connection pool between tests to prevent event-loop binding errors."""
    yield
    await engine.dispose()
