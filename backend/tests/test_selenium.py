import pytest

from app.browsers.selenium_factory import create_driver
from app.core.config import settings
from app.models import BrowserMode


@pytest.mark.selenium
def test_selenium_connection() -> None:
    driver = create_driver(BrowserMode.HEADLESS, settings.selenium_remote_url)
    try:
        driver.get("https://example.com")
        assert "example" in driver.title.lower()
    finally:
        driver.quit()
