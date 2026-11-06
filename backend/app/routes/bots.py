from fastapi import APIRouter, HTTPException, status

from app.bots.registry import registry
from app.schemas.bot import BotResponse

router = APIRouter(prefix="/bots", tags=["bots"])


@router.get("", response_model=list[BotResponse])
async def list_bots():
    return registry.list()


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: str):
    try:
        bot_class = registry.get(bot_id)
        return {"bot_id": bot_class.bot_id, "name": bot_class.name}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot '{bot_id}' not found in registry",
        ) from None
