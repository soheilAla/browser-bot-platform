from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class BotContext:
    set_challenge_id: Callable[[str], None]
    log: Callable[[str], None]
