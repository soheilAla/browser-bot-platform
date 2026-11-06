import pytest

from app.core.db import engine


@pytest.fixture(autouse=True)
async def dispose_engine_after_test():
    """Dispose connection pool between tests to prevent event-loop binding errors."""
    yield
    await engine.dispose()
