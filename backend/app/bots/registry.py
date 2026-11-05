from app.bots.base import BaseBot
from app.bots.implementations.arcaptcha import ArcaptchaBot


class BotRegistry:
    def __init__(self) -> None:
        self._bots: dict[str, type[BaseBot]] = {}

    def register(self, bot: type[BaseBot]) -> None:
        if bot.bot_id in self._bots:
            raise ValueError(f"Bot already registered: {bot.bot_id}")

        self._bots[bot.bot_id] = bot

    def get(self, bot_id: str) -> type[BaseBot]:
        try:
            return self._bots[bot_id]
        except KeyError:
            raise ValueError(f"Unknown bot: {bot_id}") from None

    def list(self) -> list[dict[str, str]]:
        return [{"bot_id": bot.bot_id, "name": bot.name} for bot in self._bots.values()]


registry = BotRegistry()

registry.register(ArcaptchaBot)
