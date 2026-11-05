import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.browsers.selenium_factory import create_driver
from app.core.config import settings
from app.models import BrowserMode, CaptchaStatus, RunStatus


class ArcaptchaBot(BaseBot):
    bot_id = "arcaptcha"
    name = "Arcaptcha Demo"

    def run(self, context: BotContext) -> BotResult:
        driver = create_driver(self.browser_mode, settings.selenium_remote_url)
        wait = WebDriverWait(driver, 15)
        challenge_id: str | None = None

        try:
            context.log("navigating", f"Navigating to {settings.target_url}")
            driver.get(settings.target_url)

            # Install network listener to capture HTTP status of /api/login
            driver.execute_script("""
                window.__login_response = null;
                const origOpen = XMLHttpRequest.prototype.open;
                const origSend = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.open = function(method, url) {
                    this._url = url;
                    return origOpen.apply(this, arguments);
                };
                XMLHttpRequest.prototype.send = function() {
                    this.addEventListener('load', function() {
                        if (this._url && this._url.includes('/api/login')) {
                            window.__login_response = {
                                status: this.status,
                                statusText: this.statusText,
                                body: this.responseText
                            };
                        }
                    });
                    return origSend.apply(this, arguments);
                };
            """)

            checkbox = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        '.arcaptcha-vue [aria-label="I\'m not robot"], #arc-checkbox',
                    )
                )
            )
            checkbox.click()
            context.log("checkbox_clicked", "Clicked ARCaptcha checkbox")

            # Extract challenge_id immediately from widget state in memory
            def extract_challenge_id_from_page(d) -> str | None:
                # Primary: extract directly from ARCaptcha Vuex store state
                # Fallback: check hidden input value for arcaptcha-token
                script = """
                    try {
                        var arc = window.arcaptcha;
                        if (!arc || !arc.widgets) return null;
                        var wId = Object.keys(arc.widgets)[0];
                        var widget = arc.widgets[wId];
                        if (!widget || !widget.vueCheckbox) return null;
                        var state = widget.vueCheckbox["$store"].state[wId];
                        if (state && state.challenge && state.challenge.challenge_id) {
                            return String(state.challenge.challenge_id);
                        }
                    } catch(e) {}
                    try {
                        var inp = document.getElementById("arcaptcha-token");
                        if (inp && inp.value) return inp.value;
                    } catch(e) {}
                    return null;
                """
                return d.execute_script(script)

            try:
                challenge_id = WebDriverWait(driver, 10).until(
                    extract_challenge_id_from_page
                )
                if challenge_id:
                    context.set_challenge_id(challenge_id)
                    context.log(
                        "challenge_extracted", f"Extracted challenge_id: {challenge_id}"
                    )
            except TimeoutException:
                context.log(
                    "challenge_missing", "Failed to obtain challenge_id within timeout"
                )

            # Check for immediate block
            time.sleep(2)
            vue_text = driver.find_element(By.CSS_SELECTOR, ".arcaptcha-vue").text
            if "Blocked" in vue_text:
                context.log("blocked", "Encountered CAPTCHA block: Are you robot?")
                return BotResult(
                    status=RunStatus.BLOCKED,
                    captcha_status=CaptchaStatus.NOT_SOLVED,
                    challenge_id=challenge_id,
                    message="Blocked by CAPTCHA anti-bot verification",
                )

            # Check if interactive puzzle overlay is present
            puzzle_overlays = driver.find_elements(
                By.ID, "arcaptcha_full_body_container"
            )
            if puzzle_overlays and puzzle_overlays[0].is_displayed():
                if self.browser_mode == BrowserMode.HEADLESS:
                    context.log(
                        "blocked", "Interactive puzzle triggered in headless mode"
                    )
                    return BotResult(
                        status=RunStatus.BLOCKED,
                        captcha_status=CaptchaStatus.NOT_SOLVED,
                        challenge_id=challenge_id,
                        message="Interactive puzzle required in headless mode",
                    )
                else:
                    context.log(
                        "awaiting_challenge",
                        "Awaiting manual puzzle solve in Headful viewer",
                    )
                    # In headful mode, wait up to 45 seconds for puzzle overlay to close
                    try:
                        WebDriverWait(driver, 45).until_not(
                            EC.visibility_of_element_located(
                                (By.ID, "arcaptcha_full_body_container")
                            )
                        )
                        context.log("challenge_solved", "Puzzle overlay cleared")
                    except TimeoutException:
                        context.log(
                            "timeout", "Timed out waiting for manual puzzle solve"
                        )
                        return BotResult(
                            status=RunStatus.BLOCKED,
                            captcha_status=CaptchaStatus.NOT_SOLVED,
                            challenge_id=challenge_id,
                            message="Timed out waiting for puzzle solution in noVNC",
                        )

            # Enter configured username and password
            email = wait.until(EC.visibility_of_element_located((By.ID, "email")))
            email.clear()
            email.send_keys(settings.arcaptcha_username)

            password = driver.find_element(By.ID, "password")
            password.clear()
            password.send_keys(settings.arcaptcha_password)
            context.log(
                "credentials_entered", "Entered configured credentials into form"
            )

            submit_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(text(), "Login")]')
                )
            )
            submit_btn.click()
            context.log("form_submitted", "Clicked login submit button")

            # Dual-layer verification: HTTP response status + UI Toast
            http_status: int | None = None
            response_body: str | None = None

            # Poll for /api/login response (up to 10s)
            def poll_http_response(d) -> dict | None:
                resp = d.execute_script("return window.__login_response;")
                if resp and "status" in resp:
                    return resp
                # Fallback: check PerformanceResourceTiming
                perf_status = d.execute_script("""
                    let entries = performance.getEntriesByName(
                        'https://demo.arcaptcha.co/api/login'
                    );
                    if (entries.length > 0 && entries[0].responseStatus) {
                        return { status: entries[0].responseStatus, body: '' };
                    }
                    return null;
                """)
                return perf_status

            try:
                login_resp = WebDriverWait(driver, 10).until(poll_http_response)
                if isinstance(login_resp, dict):
                    http_status = int(login_resp["status"])
                    response_body = login_resp.get("body")
                    context.log(
                        "http_response",
                        f"Login API responded with HTTP {http_status}: {response_body}",
                    )
            except TimeoutException:
                context.log(
                    "http_timeout", "Timed out waiting for /api/login HTTP response"
                )

            # Check UI Toast message
            toast_text: str | None = None
            toast_success: bool = False
            try:
                toast = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".Vue-Toastification__toast")
                    )
                )
                toast_class = toast.get_attribute("class") or ""
                toast_success = "toast--success" in toast_class

                # Use textContent to avoid CSS bounce entrance animation blanking
                body_els = driver.find_elements(
                    By.CSS_SELECTOR, ".Vue-Toastification__toast-body"
                )
                if body_els:
                    toast_text = (
                        body_els[0].get_attribute("textContent") or ""
                    ).strip()
                if not toast_text:
                    toast_text = (
                        (toast.get_attribute("textContent") or "")
                        .replace("×", "")
                        .strip()
                    )

                context.log("toast_received", f"UI toast: {toast_text}")
            except TimeoutException:
                pass

            result_msg = (
                toast_text or response_body or f"HTTP {http_status or 'unknown'}"
            )

            if http_status == 200 or toast_success:
                return BotResult(
                    status=RunStatus.SUCCESS,
                    captcha_status=CaptchaStatus.SOLVED,
                    challenge_id=challenge_id,
                    message=f"HTTP 200 OK - {result_msg}",
                )
            else:
                code_label = f"HTTP {http_status}" if http_status else "Failed"
                return BotResult(
                    status=RunStatus.FAILED,
                    captcha_status=CaptchaStatus.VERIFICATION_FAILED,
                    challenge_id=challenge_id,
                    message=f"{code_label} - {result_msg}",
                )

        except Exception as e:
            context.log("error", f"Technical error during execution: {e}")
            return BotResult(
                status=RunStatus.FAILED,
                captcha_status=CaptchaStatus.PENDING,
                challenge_id=challenge_id,
                message=str(e),
            )
        finally:
            driver.quit()
