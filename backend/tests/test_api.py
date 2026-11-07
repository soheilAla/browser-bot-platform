import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.db import SessionLocal
from app.main import app
from app.models import BrowserMode, Run, RunEvent, RunStatus


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_list_bots(client: AsyncClient) -> None:
    response = await client.get("/api/bots")
    assert response.status_code == 200
    bots = response.json()
    assert isinstance(bots, list)
    assert len(bots) >= 1

    bot_ids = [b["bot_id"] for b in bots]
    assert "arcaptcha" in bot_ids


@pytest.mark.asyncio
async def test_get_bot_detail(client: AsyncClient) -> None:
    response = await client.get("/api/bots/arcaptcha")
    assert response.status_code == 200
    data = response.json()
    assert data["bot_id"] == "arcaptcha"
    assert "Arcaptcha" in data["name"]

    res_404 = await client.get("/api/bots/nonexistent_bot")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_create_run_success(client: AsyncClient) -> None:
    payload = {
        "bot_id": "test_bot",
        "browser_mode": "headless",
    }
    response = await client.post("/api/runs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["bot_id"] == "test_bot"
    assert data["browser_mode"] == "headless"
    assert data["status"] == "pending"
    assert data["bot_metadata"] == {}
    assert "id" in data
    run_id = uuid.UUID(data["id"])

    async with SessionLocal() as session:
        await session.execute(delete(Run).where(Run.id == run_id))
        await session.commit()


@pytest.mark.asyncio
async def test_create_run_unknown_bot_rejected(client: AsyncClient) -> None:
    payload = {
        "bot_id": "unknown_bot",
        "browser_mode": "headless",
    }
    response = await client.post("/api/runs", json=payload)
    assert response.status_code == 400
    assert "Unknown bot_id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_filter_runs(client: AsyncClient) -> None:
    response = await client.get("/api/runs?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert isinstance(data["items"], list)

    res_status = await client.get("/api/runs?run_status=pending")
    assert res_status.status_code == 200
    for item in res_status.json()["items"]:
        assert item["status"] == "pending"


@pytest.mark.asyncio
async def test_get_run_and_events(client: AsyncClient) -> None:
    async with SessionLocal() as session:
        run = Run(
            bot_id="test_bot",
            browser_mode=BrowserMode.HEADLESS,
            status=RunStatus.PENDING,
            bot_metadata={"test_key": "test_val"},
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

        session.add(
            RunEvent(
                run_id=run_id,
                event_type="test_event",
                message="This is a test event",
            )
        )
        await session.commit()

    try:
        res_run = await client.get(f"/api/runs/{run_id}")
        assert res_run.status_code == 200
        run_data = res_run.json()
        assert run_data["id"] == str(run_id)
        assert run_data["bot_metadata"] == {"test_key": "test_val"}

        res_events = await client.get(f"/api/runs/{run_id}/events")
        assert res_events.status_code == 200
        events = res_events.json()
        assert len(events) >= 1
        assert events[0]["event_type"] == "test_event"
        assert events[0]["message"] == "This is a test event"

        missing_id = uuid.uuid4()
        res_missing = await client.get(f"/api/runs/{missing_id}")
        assert res_missing.status_code == 404
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Run).where(Run.id == run_id))
            await session.commit()


@pytest.mark.asyncio
async def test_cancel_pending_run(client: AsyncClient) -> None:
    create_res = await client.post(
        "/api/runs", json={"bot_id": "test_bot", "browser_mode": "headless"}
    )
    assert create_res.status_code == 201
    run_id = uuid.UUID(create_res.json()["id"])

    try:
        cancel_res = await client.post(f"/api/runs/{run_id}/cancel")
        assert cancel_res.status_code == 200
        data = cancel_res.json()
        assert data["status"] == "cancelled"
        assert data["error_message"] == "Cancelled by user"
        assert data["finished_at"] is not None

        events_res = await client.get(f"/api/runs/{run_id}/events")
        assert events_res.status_code == 200
        events = events_res.json()
        event_types = [e["event_type"] for e in events]
        assert "cancelled" in event_types

        # Attempting to cancel again should fail with 400
        cancel_again = await client.post(f"/api/runs/{run_id}/cancel")
        assert cancel_again.status_code == 400
        assert "Only active runs can be cancelled" in cancel_again.json()["detail"]
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Run).where(Run.id == run_id))
            await session.commit()
