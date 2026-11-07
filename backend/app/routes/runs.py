import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots.registry import registry
from app.core.db import get_session
from app.models import Run, RunEvent, RunStatus
from app.schemas.run import (
    RunCreateRequest,
    RunEventResponse,
    RunListResponse,
    RunResponse,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        registry.get(payload.bot_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown bot_id '{payload.bot_id}'. Bot is not registered.",
        ) from None

    run = Run(
        bot_id=payload.bot_id,
        browser_mode=payload.browser_mode,
        status=RunStatus.PENDING,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    return run


@router.get("", response_model=RunListResponse)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0),
    run_status: RunStatus | None = Query(default=None),
    bot_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    query = select(Run)
    count_query = select(func.count()).select_from(Run)

    if run_status:
        query = query.where(Run.status == run_status)
        count_query = count_query.where(Run.status == run_status)

    if bot_id:
        query = query.where(Run.bot_id == bot_id)
        count_query = count_query.where(Run.bot_id == bot_id)

    total_res = await session.execute(count_query)
    total = total_res.scalar_one()

    query = (
        query.order_by(Run.created_at.desc(), Run.id.desc()).offset(offset).limit(limit)
    )
    runs_res = await session.execute(query)
    runs = runs_res.scalars().all()

    return RunListResponse(
        items=[RunResponse.model_validate(r) for r in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )
    return run


@router.get("/{run_id}/events", response_model=list[RunEventResponse])
async def get_run_events(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )

    stmt = (
        select(RunEvent)
        .where(RunEvent.run_id == run_id)
        .order_by(RunEvent.created_at.asc())
    )
    result = await session.execute(stmt)
    events = result.scalars().all()

    return events


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )

    active_statuses = (
        RunStatus.PENDING,
        RunStatus.RUNNING,
        RunStatus.AWAITING_CHALLENGE,
    )
    if run.status not in active_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot cancel run with status '{run.status}'. "
                "Only active runs can be cancelled."
            ),
        )

    now = datetime.now(UTC)
    run.status = RunStatus.CANCELLED
    run.finished_at = now
    run.error_message = "Cancelled by user"

    session.add(
        RunEvent(
            run_id=run.id,
            event_type="cancelled",
            message="Run cancelled by user",
            created_at=now,
        )
    )
    await session.commit()
    await session.refresh(run)

    return run
