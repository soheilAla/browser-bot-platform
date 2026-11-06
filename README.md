# Browser Bot Platform

An extensible web platform for running and monitoring browser bots with persistent execution history, headless/headful modes, and live browser streaming via noVNC.

---

## 1. Quick Start & Deployment

### Prerequisites

- Docker Engine 24+ & Docker Compose v2
- Linux, macOS, or Windows (WSL2)
- 4 GB RAM minimum (`/dev/shm` 2 GB allocated for Chrome)

### Setup

```bash
git clone git@github.com:soheilAla/browser-bot-platform.git
cd browser_bot_platform

cp .env.example .env
```

Set credentials and database password in `.env`.

```bash
docker compose up -d --build
```

Compose automatically boots PostgreSQL, runs database migrations via Alembic, starts the FastAPI backend, background worker, patched Selenium Chrome container, and Vue 3 frontend.

Verify services:

```bash
docker compose ps
```

---

## 2. Platform Usage

### Access Points

- **Web Dashboard:** [http://localhost:3000](http://localhost:3000)
- **REST API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live Browser Stream (noVNC):** [http://localhost:7900/?autoconnect=1](http://localhost:7900/?autoconnect=1)

### Running a Bot

1. Open the Web Dashboard at `http://localhost:3000`.
2. Select **Arcaptcha Demo (`arcaptcha`)** from the dropdown.
3. Choose **Headful** or **Headless** mode, then click **Trigger Run**.
4. Click on any run row in the history table to inspect details:
   - Status (`SUCCESS`, `BLOCKED`, `FAILED`)
   - Duration and timestamps
   - Extracted `challenge_id` and `captcha_status`
   - Real-time audit event timeline

### Viewing the Browser in Headful Mode

The browser runs inside an Xvfb virtual display exported via noVNC on port `7900`:

- **Desktop:** Open `http://localhost:7900/?autoconnect=1` directly in your browser (default password is "secret").
- **Remote Server / VPS:** Forward port 7900 over SSH from your laptop:
  ```bash
  ssh -N -L 3000:127.0.0.1:3000 -L 7900:127.0.0.1:7900 user@<VPS_IP>
  ```
  Then open `http://localhost:7900/?autoconnect=1` locally.

_Note on interactive challenges:_ In headful mode, if a puzzle modal appears, the bot pauses and waits up to 45 seconds for a manual solve in the viewer before proceeding with form submission. In headless mode, it records the extracted `challenge_id` and safely reports the outcome.

---

## 3. Extensibility Guide: Adding a New Bot

Bot implementations are decoupled from the platform core, storage, and UI. Adding a new bot requires no changes to database schemas or API routes.

### Step 1: Create the Bot Class

Subclass `BaseBot` (`backend/app/bots/base.py`):

```python
# backend/app/bots/implementations/quotes_bot.py
from selenium.webdriver.common.by import By
from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.browsers.selenium_factory import create_driver
from app.core.config import settings
from app.models import RunStatus

class QuotesBot(BaseBot):
    bot_id = "quotes_bot"
    name = "Quotes Scraper"

    def run(self, context: BotContext) -> BotResult:
        driver = create_driver(context.browser_mode, settings.selenium_remote_url)
        try:
            context.log("navigating", "Opening target URL")
            driver.get("https://quotes.toscrape.com")

            quote = driver.find_element(By.CSS_SELECTOR, ".quote .text").text
            context.log("extracted", f"Found quote: {quote[:30]}...")

            # Persist bot-specific telemetry into JSONB metadata
            context.update_metadata({"quote": quote})

            return BotResult(
                status=RunStatus.SUCCESS,
                message="Quote extracted successfully",
                metadata={"status": "complete"}
            )
        except Exception as e:
            return BotResult(status=RunStatus.FAILED, message=str(e))
        finally:
            driver.quit()
```

### Step 2: Register the Bot

Register the bot in `backend/app/bots/registry.py`:

```python
from app.bots.implementations.quotes_bot import QuotesBot

registry.register(QuotesBot)
```

The bot will automatically appear in the Web UI dropdown and `GET /api/bots`.

---

## 4. Tests

### Inside Docker (Recommended)

```bash
docker compose exec api pytest -v
```

### Local (with uv)

```bash
cd backend
uv run pytest -v
```

Tests cover API endpoints, atomic queue claiming, crash recovery, JSONB metadata patching, Selenium remote connection, and `challenge_id` persistence across success and failure paths.

---

## 5. Anti-Bot Evasion Benchmark (Bonus)

Full reverse-engineering analysis, client-side detection vectors, and the empirical ablation study are documented in [`anti-bot-investigation.md`](anti-bot-investigation.md).

---

## 6. Data Persistence & Troubleshooting

- **Data Persistence:** PostgreSQL data is stored on named volume `pg_data`. Run records and event logs survive `docker compose down && docker compose up -d`.
- **Port Conflicts:** If `3000`, `8000`, `5434`, or `7900` are occupied, adjust port mappings in `docker-compose.yml`.
- **Worker Crash Recovery:** If the worker container restarts during execution, it automatically flags interrupted runs as `FAILED` on startup so they do not stay stuck in `RUNNING`.
