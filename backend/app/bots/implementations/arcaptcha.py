from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.bots.settings.arcaptcha import bot_settings
from app.browsers.selenium_factory import create_driver
from app.core.config import settings
from app.models import BrowserMode, RunStatus
from app.schemas.arcaptcha import ArcaptchaMetadata, CaptchaStatus

# Intercepts login responses and decrypts challenge creation payload
JS_NETWORK_HOOK = """
window.__login_response = null;
window.__captured_challenge_id = null;

function decryptArcaptcha(buf) {
    try {
        var t = buf instanceof ArrayBuffer
            ? new Uint8Array(buf)
            : new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
        if (t.length < 5) return null;
        var e = t[0], r = t[1], n = t[2], o = t[3], s = 90;
        var c = t.length - 4;
        var u = new Uint8Array(c);
        var l = 4;
        for (var f = 0; f < c; f++) {
            var p = t[l];
            l++;
            e = (e + r) & 255;
            r = (r ^ n) & 255;
            n = (n + o) & 255;
            o = (o ^ e) & 255;
            var d = (e + o) & 255;
            var a_val = 255 & ((p >>> 3) | (p << 5));
            var h = ((a_val - s) & 255) ^ d;
            u[f] = h;
            s = p;
        }
        var v = u[c - 1];
        if (v > c - 1) return null;
        var g = c - 1 - v;
        var m = u.subarray(0, g);
        var text = new TextDecoder('utf-8').decode(m);
        return JSON.parse(text);
    } catch(err) {
        return null;
    }
}

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
        if (this._url && this._url.includes('create?id=')) {
            var dec = decryptArcaptcha(this.response);
            if (dec && dec.content && dec.content.challenge_id) {
                window.__captured_challenge_id = String(dec.content.challenge_id);
            }
        }
    });
    return origSend.apply(this, arguments);
};
"""

# Reads decrypted challenge_id from network capture or Vuex state
JS_EXTRACT_CHALLENGE = """
if (window.__captured_challenge_id) {
    return window.__captured_challenge_id;
}
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

# Polls for login response from listener or performance API
JS_POLL_LOGIN_RESPONSE = """
var resp = window.__login_response;
if (resp && "status" in resp) {
    return resp;
}
var entries = performance.getEntriesByType('resource').filter(
    function(e) { return e.name.indexOf('/api/login') !== -1; }
);
if (entries.length > 0 && entries[0].responseStatus) {
    return { status: entries[0].responseStatus, body: '' };
}
return null;
"""


class ArcaptchaBot(BaseBot):
    bot_id = "arcaptcha"
    name = "Arcaptcha Demo"

    def run(self, context: BotContext) -> BotResult:
        driver = create_driver(context.browser_mode, settings.selenium_remote_url)
        wait = WebDriverWait(driver, 15)
        challenge_id: str | None = None

        try:
            context.log("navigating", f"Navigating to {bot_settings.target_url}")
            driver.get(bot_settings.target_url)
            driver.execute_script(JS_NETWORK_HOOK)

            self._click_checkbox(driver, wait, context)

            challenge_id = self._extract_challenge(driver, wait, context)

            early_exit = self._handle_challenge_gate(
                driver, wait, context, challenge_id
            )
            if early_exit:
                return early_exit

            self._fill_credentials_and_submit(driver, wait, context)

            return self._verify_outcome(driver, context, challenge_id)

        except Exception as e:
            context.log("error", f"Technical error during execution: {e}")
            meta = ArcaptchaMetadata(
                challenge_id=challenge_id,
                captcha_status=CaptchaStatus.UNKNOWN,
            ).model_dump()
            return BotResult(status=RunStatus.FAILED, message=str(e), metadata=meta)
        finally:
            driver.quit()

    def _click_checkbox(
        self, driver: WebDriver, wait: WebDriverWait, context: BotContext
    ) -> None:
        selector = '.arcaptcha-vue [aria-label="I\'m not robot"], #arc-checkbox'
        checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        checkbox.click()
        context.log("checkbox_clicked", "Clicked ARCaptcha checkbox")

    def _extract_challenge(
        self, driver: WebDriver, wait: WebDriverWait, context: BotContext
    ) -> str | None:
        try:
            cid = WebDriverWait(driver, 10).until(
                lambda d: d.execute_script(JS_EXTRACT_CHALLENGE)
            )
            if cid:
                meta = ArcaptchaMetadata(
                    challenge_id=cid,
                    captcha_status=CaptchaStatus.PENDING,
                ).model_dump()
                context.update_metadata(meta)
                context.log("challenge_extracted", f"Extracted challenge_id: {cid}")
            return cid
        except TimeoutException:
            context.log(
                "challenge_missing", "Failed to obtain challenge_id within timeout"
            )
            return None

    def _handle_challenge_gate(
        self,
        driver: WebDriver,
        wait: WebDriverWait,
        context: BotContext,
        challenge_id: str | None,
    ) -> BotResult | None:
        # Check for immediate block
        vue_el = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".arcaptcha-vue"))
        )
        if "Blocked" in vue_el.text:
            context.log("blocked", "Encountered CAPTCHA block: Are you robot?")
            meta = ArcaptchaMetadata(
                challenge_id=challenge_id,
                captcha_status=CaptchaStatus.NOT_SOLVED,
            ).model_dump()
            return BotResult(
                status=RunStatus.BLOCKED,
                message="Blocked by CAPTCHA anti-bot verification",
                metadata=meta,
            )

        # Check interactive puzzle overlay
        overlays = driver.find_elements(By.ID, "arcaptcha_full_body_container")
        if overlays and overlays[0].is_displayed():
            if context.browser_mode == BrowserMode.HEADLESS:
                context.log(
                    "puzzle_skipped",
                    "Interactive puzzle required; skipping solve in headless mode",
                )
            else:
                context.log(
                    "awaiting_challenge",
                    "Awaiting manual puzzle solve in Headful viewer",
                )
                try:
                    WebDriverWait(driver, 45).until_not(
                        EC.visibility_of_element_located(
                            (By.ID, "arcaptcha_full_body_container")
                        )
                    )
                    context.log("challenge_solved", "Puzzle overlay cleared")
                except TimeoutException:
                    context.log("timeout", "Timed out waiting for manual puzzle solve")
                    meta = ArcaptchaMetadata(
                        challenge_id=challenge_id,
                        captcha_status=CaptchaStatus.NOT_SOLVED,
                    ).model_dump()
                    return BotResult(
                        status=RunStatus.FAILED,
                        message="Timed out waiting for puzzle solution in noVNC",
                        metadata=meta,
                    )
        return None

    def _fill_credentials_and_submit(
        self, driver: WebDriver, wait: WebDriverWait, context: BotContext
    ) -> None:
        email = wait.until(EC.presence_of_element_located((By.ID, "email")))
        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            'arguments[0].dispatchEvent(new Event("input"));',
            email,
            bot_settings.email,
        )

        password = wait.until(EC.presence_of_element_located((By.ID, "password")))
        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            'arguments[0].dispatchEvent(new Event("input"));',
            password,
            bot_settings.password,
        )
        context.log("credentials_entered", "Entered configured credentials into form")

        btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//button[contains(text(), "Login")]')
            )
        )
        driver.execute_script("arguments[0].click();", btn)
        context.log("form_submitted", "Clicked login submit button")

    def _verify_outcome(
        self, driver: WebDriver, context: BotContext, challenge_id: str | None
    ) -> BotResult:
        http_status, response_body = self._poll_login_http(driver, context)

        toast_text, toast_success = self._read_toast(driver, context)

        result_msg = toast_text or response_body or f"HTTP {http_status or 'unknown'}"

        if http_status == 200 and toast_success:
            meta = ArcaptchaMetadata(
                challenge_id=challenge_id,
                captcha_status=CaptchaStatus.SOLVED,
            ).model_dump()
            return BotResult(
                status=RunStatus.SUCCESS,
                message=f"HTTP 200 OK - {result_msg}",
                metadata=meta,
            )
        else:
            code_label = f"HTTP {http_status}" if http_status else "Failed"
            c_status = (
                CaptchaStatus.NOT_SOLVED
                if "solve captcha" in result_msg.lower()
                else CaptchaStatus.VERIFICATION_FAILED
            )
            meta = ArcaptchaMetadata(
                challenge_id=challenge_id,
                captcha_status=c_status,
            ).model_dump()
            return BotResult(
                status=RunStatus.FAILED,
                message=f"{code_label} - {result_msg}",
                metadata=meta,
            )

    def _poll_login_http(
        self, driver: WebDriver, context: BotContext
    ) -> tuple[int | None, str | None]:
        try:
            login_resp = WebDriverWait(driver, 10).until(
                lambda d: d.execute_script(JS_POLL_LOGIN_RESPONSE)
            )
            if isinstance(login_resp, dict):
                code = int(login_resp["status"])
                body = login_resp.get("body")
                context.log(
                    "http_response",
                    f"Login API responded with HTTP {code}: {body}",
                )
                return code, body
        except TimeoutException:
            context.log(
                "http_timeout", "Timed out waiting for /api/login HTTP response"
            )
        return None, None

    def _read_toast(
        self, driver: WebDriver, context: BotContext
    ) -> tuple[str | None, bool]:
        try:
            toast = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".Vue-Toastification__toast")
                )
            )
            toast_class = toast.get_attribute("class") or ""
            is_success = "toast--success" in toast_class

            # Read textContent from body to avoid CSS bounce entrance animation blanking
            body_els = driver.find_elements(
                By.CSS_SELECTOR, ".Vue-Toastification__toast-body"
            )
            text = (
                body_els[0].get_attribute("textContent")
                if body_els
                else toast.get_attribute("textContent")
            ) or ""
            clean_text = text.replace("×", "").strip()

            context.log("toast_received", f"UI toast: {clean_text}")
            return clean_text, is_success
        except TimeoutException:
            return None, False
