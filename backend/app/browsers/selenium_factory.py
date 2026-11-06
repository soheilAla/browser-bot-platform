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
        # Strip HeadlessChrome token from User-Agent
        options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
        )

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

    driver = webdriver.Remote(
        command_executor=remote_url,
        options=options,
    )

    if browser_mode == BrowserMode.HEADLESS:
        # Align screen resolution and permissions to eliminate headless anomalies
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    const setProp = (obj, prop, val) =>
                        Object.defineProperty(obj, prop, { get: () => val });
                    setProp(Screen.prototype, 'width', 1920);
                    setProp(Screen.prototype, 'height', 1080);
                    setProp(Screen.prototype, 'availWidth', 1920);
                    setProp(Screen.prototype, 'availHeight', 1058);

                    if (window.Notification) {
                        setProp(Notification, 'permission', 'default');
                    }
                """
            },
        )

    return driver
