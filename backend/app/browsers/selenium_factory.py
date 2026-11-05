from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

from app.models import BrowserMode


def create_driver(
    browser_mode: BrowserMode,
    remote_url: str = "http://localhost:4444",
) -> WebDriver:
    options = Options()

    if browser_mode == BrowserMode.HEADLESS:
        options.add_argument("--headless=new")

    # Explicit resolution required for headless Linux/Docker
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Disable Blink automation flag and automation infobars
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Enable WebGL on software Xvfb displays (prevents empty WebGL fingerprint)
    options.add_argument("--ignore-gpu-blocklist")
    options.add_argument("--enable-webgl")

    return webdriver.Remote(
        command_executor=remote_url,
        options=options,
    )
