from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.bots.context import BotContext
from app.models import CaptchaStatus, RunStatus


@dataclass
class BotResult:
    status: RunStatus
    captcha_status: CaptchaStatus
    challenge_id: str | None = None
    message: str | None = None


class BaseBot(ABC):
    bot_id: str
    name: str

    def __init__(self, browser_mode) -> None:
        self.browser_mode = browser_mode

    @abstractmethod
    def run(self, context: BotContext) -> BotResult:
        """Execute the bot workflow and return outcome."""
        raise NotImplementedError
