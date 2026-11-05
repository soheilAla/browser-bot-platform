from app.bots.base import BaseBot
from app.bots.context import BotContext
from app.browsers.selenium_factory import create_driver
from app.models import BrowserMode


class ArcaptchaBot(BaseBot):
    bot_id = "arcaptcha"
    name = "Arcaptcha Demo"

    def __init__(self, browser_mode: BrowserMode) -> None:
        self.browser_mode = browser_mode

    def run(self, context: BotContext) -> None:
        driver = create_driver(self.browser_mode)

        try:
            context.log("Opening Arcaptcha demo")
            driver.get("https://demo.arcaptcha.co")

        finally:
            driver.quit()
