from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.bots.context import BotContext
from app.models import RunStatus


@dataclass
class BotResult:
    status: RunStatus
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseBot(ABC):
    bot_id: str
    name: str

    def __init__(self, browser_mode) -> None:
        self.browser_mode = browser_mode

    @abstractmethod
    def run(self, context: BotContext) -> BotResult:
        """Execute the bot workflow and return outcome."""
        raise NotImplementedError
