from app.browsers.selenium_factory import create_driver
from app.models import BrowserMode


def test_selenium_connection() -> None:
    driver = create_driver(BrowserMode.HEADLESS)
    try:
        driver.get("https://example.com")
        assert "Example" in driver.title
    finally:
        driver.quit()
