from abc import ABC, abstractmethod

from app.bots.context import BotContext


class BaseBot(ABC):
    bot_id: str
    name: str

    @abstractmethod
    def run(self, context: BotContext) -> None:
        """Execute the bot workflow."""
        raise NotImplementedError
