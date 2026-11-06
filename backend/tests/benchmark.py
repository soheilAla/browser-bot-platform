import argparse
import sys
import time
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from app.bots.settings.arcaptcha import bot_settings
from app.browsers.selenium_factory import create_driver
from app.core.config import settings
from app.models import BrowserMode


def run_benchmark(trials: int = 5, mode: BrowserMode = BrowserMode.HEADFUL) -> None:
    print("=" * 65)
    print(f"🔬 ARCAPTCHA STEALTH BENCHMARK ({trials} TRIALS)")
    print(f"Target: {bot_settings.target_url} | Mode: {mode.value}")
    print("=" * 65)

    results = []

    for i in range(1, trials + 1):
        driver = create_driver(mode, settings.selenium_remote_url)
        start_time = time.time()
        verdict = "UNKNOWN"
        detail = ""

        try:
            driver.get(bot_settings.target_url)
            wait = WebDriverWait(driver, 10)

            box = wait.until(
                lambda d: d.find_element(
                    By.CSS_SELECTOR,
                    '.arcaptcha-vue [aria-label="I\'m not robot"], #arc-checkbox',
                )
            )
            box.click()

            # Poll for challenge outcome (puzzle modal rendered vs. blocked error)
            def check_verdict(d) -> dict | None:
                return d.execute_script("""
                    var arc = window.arcaptcha;
                    if (!arc || !arc.widgets) return null;
                    var wId = Object.keys(arc.widgets)[0];
                    var widget = arc.widgets[wId];
                    if (!widget || !widget.vueCheckbox) return null;
                    var s = widget.vueCheckbox["$store"].state[wId];
                    if (!s) return null;

                    var vueEl = document.querySelector('.arcaptcha-vue');
                    var vueText = vueEl ? vueEl.innerText : '';

                    if (s.widget_error || vueText.includes('Blocked')) {
                        return {
                            verdict: 'BLOCKED',
                            detail: s.widget_error || 'Blocked by anti-bot'
                        };
                    }

                    var overlay = document.getElementById(
                        'arcaptcha_full_body_container'
                    );
                    var hasPuzzle = document.querySelectorAll(
                        '.arc-puzzle'
                    ).length > 0;
                    var isOpen = s.boxIsOpen || s.challengeIsLoaded;
                    var isVisible = overlay && overlay.style.display !== 'none';

                    if (isOpen || hasPuzzle || isVisible) {
                        return {
                            verdict: 'UNBLOCKED (PUZZLE)',
                            detail: 'Puzzle challenge modal rendered'
                        };
                    }

                    return null;
                """)

            outcome = WebDriverWait(driver, 10).until(check_verdict)
            elapsed = time.time() - start_time
            if isinstance(outcome, dict):
                verdict = str(outcome.get("verdict", "UNKNOWN"))
                detail = str(outcome.get("detail", ""))
            else:
                verdict = "UNKNOWN"
                detail = "No response"

            results.append(
                {
                    "trial": i,
                    "verdict": verdict,
                    "detail": detail,
                    "duration": elapsed,
                }
            )

            print(
                f"[Trial {i:02d}/{trials:02d}] "
                f"Verdict: {verdict:<20} | "
                f"Detail: {detail:<32} | "
                f"Latency: {elapsed:.2f}s"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            print(
                f"[Trial {i:02d}/{trials:02d}] Verdict: TIMEOUT/ERROR ({e})",
                file=sys.stderr,
            )
            results.append(
                {
                    "trial": i,
                    "verdict": "ERROR",
                    "detail": str(e),
                    "duration": elapsed,
                }
            )
        finally:
            driver.quit()

    unblocked = sum(1 for r in results if "UNBLOCKED" in r["verdict"])
    blocked = sum(1 for r in results if r["verdict"] == "BLOCKED")
    errors = sum(1 for r in results if r["verdict"] == "ERROR")
    success_rate = (unblocked / trials) * 100

    print("=" * 65)
    print("📊 BENCHMARK SUMMARY")
    print(f"Total Trials: {trials}")
    print(f"Unblocked:    {unblocked} ({success_rate:.1f}%)")
    print(f"Blocked:      {blocked}")
    if errors:
        print(f"Errors:       {errors}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ARCaptcha stealth benchmark")
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of trials to execute (default: 5)",
    )
    parser.add_argument(
        "--mode",
        choices=["headful", "headless"],
        default="headful",
        help="Browser mode (default: headful)",
    )
    args = parser.parse_args()

    browser_mode = (
        BrowserMode.HEADFUL if args.mode == "headful" else BrowserMode.HEADLESS
    )
    run_benchmark(trials=args.trials, mode=browser_mode)
