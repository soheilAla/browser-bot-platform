import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models import BrowserMode


@dataclass
class BotContext:
    run_id: uuid.UUID
    browser_mode: BrowserMode
    update_metadata: Callable[[dict[str, Any]], None]
    log: Callable[[str, str], None]  # (event_type, message)
