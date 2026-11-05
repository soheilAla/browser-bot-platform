import uuid
from collections.abc import Callable
from dataclasses import dataclass

from app.models import BrowserMode


@dataclass
class BotContext:
    run_id: uuid.UUID
    browser_mode: BrowserMode
    set_challenge_id: Callable[[str], None]
    log: Callable[[str, str], None]  # (event_type, message)
