# Browser Bot Platform

An extensible web platform for running and monitoring browser bots with persistent execution history, headless/headful modes, and live browser streaming via noVNC.

## 1. Quick Start & Deployment

### Prerequisites

- Docker Engine 24+ & Docker Compose v2
- Linux, macOS, or Windows (WSL2)
- 2 CPU cores minimum
- 4 GB RAM minimum (`/dev/shm` 2 GB allocated for Chrome)

### Setup

```bash
git clone https://github.com/soheilAla/browser-bot-platform.git
cd browser-bot-platform

cp .env.example .env
```

Set bot credentials and database password in `.env`.

```bash
docker compose up -d --build
```

Compose automatically boots PostgreSQL, runs database migrations via Alembic, starts the FastAPI backend, background worker, patched Selenium Chrome container, and Vue 3 frontend.

Verify services:

```bash
docker compose ps
```

## 2. Platform Usage

### Access Points

- **Web Dashboard:** [http://localhost:3000](http://localhost:3000)
- **REST API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live Browser Stream (noVNC):** [http://localhost:7900/?autoconnect=1](http://localhost:7900/?autoconnect=1)

### Running & Cancelling a Bot

1. Open the Web Dashboard at `http://localhost:3000`.
2. Select **Arcaptcha Demo (`arcaptcha`)** from the dropdown.
3. Choose **Headful** or **Headless** mode, then click **Trigger Run**.
4. Active runs can be cancelled at any time by clicking **Cancel** in the table row or inside the detail modal.
5. Click on any run row in the history table to inspect details:
   - Status (`SUCCESS`, `BLOCKED`, `FAILED`, `CANCELLED`)
   - Duration and timestamps
   - Extracted `challenge_id` and `captcha_status`
   - Real-time audit event timeline

### Viewing the Browser in Headful Mode

The browser runs inside an Xvfb virtual display exported via noVNC on port `7900`:

- **Desktop:** Open `http://localhost:7900/?autoconnect=1` directly in your browser (default password is "secret").

- **Remote Server / VPS:** Forward Web UI (3000), API docs (8000), and noVNC (7900) over SSH from your laptop:
  ```bash
  ssh -N -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 -L 7900:127.0.0.1:7900 user@<VPS_IP>
  ```
  Then open `http://localhost:3000`, `http://localhost:8000/docs`, and `http://localhost:7900/?autoconnect=1` locally.

_Note on interactive challenges:_ In headful mode, if a puzzle modal appears, the bot pauses and waits up to 45 seconds for a manual solve in the viewer before proceeding with form submission. In headless mode, it records the extracted `challenge_id` and skips CAPTCHA solving.

## 3. Extensibility Guide: Adding a New Bot

The platform decouples bot logic from execution orchestration, persistent storage, and API contracts.

Adding a new bot requires **zero modifications** to database tables, migration scripts, or frontend components. The Web UI dynamically fetches available bots from `GET /api/bots` and automatically adds the new bot to the launch dropdown.

### Step 1: Define Bot Settings & Secrets (Optional)

If your bot requires target URLs, credentials, or API keys, isolate them in `backend/app/bots/settings/<bot_id>.py` using `pydantic-settings`. Do **not** modify platform core settings (`app/core/config.py`).

```python
# backend/app/bots/settings/quotes.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class QuotesBotSettings(BaseSettings):
    target_url: str
    api_key: str

    model_config = SettingsConfigDict(
        env_prefix="QUOTES_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

quotes_settings = QuotesBotSettings() # type: ignore
```

Add secrets to the `.env` (e.g. `QUOTES_API_KEY=xyz`).

### Step 2: Define Metadata Schema (Optional)

Platform storage uses a PostgreSQL `JSONB` column (`runs.bot_metadata`) to store bot-specific telemetry without altering SQL tables. Define a Pydantic schema in `backend/app/schemas/<bot_id>.py` to model your bot's metadata contract:

```python
# backend/app/schemas/quotes.py
from pydantic import BaseModel

class QuotesMetadata(BaseModel):
    quotes_extracted: int = 0
    top_author: str | None = None
```

### Step 3: Implement the Bot Class

Subclass `BaseBot` (`backend/app/bots/base.py`) and implement `run(self, context: BotContext) -> BotResult`:

```python
# backend/app/bots/implementations/quotes_bot.py
from selenium.webdriver.common.by import By
from app.bots.base import BaseBot, BotResult
from app.bots.context import BotContext
from app.bots.settings.quotes import quotes_settings
from app.browsers.selenium_factory import create_driver
from app.core.config import settings
from app.models import RunStatus
from app.schemas.quotes import QuotesMetadata

class QuotesBot(BaseBot):
    bot_id = "quotes_bot"      # Unique identifier used in API and database
    name = "Quotes Scraper"    # Display name in Web UI dropdown

    def run(self, context: BotContext) -> BotResult:
        # 1. Initialize standardized Remote WebDriver
        driver = create_driver(context.browser_mode, settings.selenium_remote_url)
        try:
            # 2. Log timeline events in real time (persisted to run_events table)
            context.log("navigating", f"Opening {quotes_settings.target_url}")
            driver.get(quotes_settings.target_url)

            quote_elements = driver.find_elements(By.CSS_SELECTOR, ".quote")
            first_quote = quote_elements[0].find_element(By.CSS_SELECTOR, ".text").text
            author = quote_elements[0].find_element(By.CSS_SELECTOR, ".author").text
            context.log("extracted", f"Scraped top quote by {author}")

            # 3. Incrementally update JSONB metadata in DB during execution
            meta = QuotesMetadata(quotes_extracted=len(quote_elements), top_author=author)
            context.update_metadata(meta.model_dump())

            # 4. Return outcome with final status
            return BotResult(
                status=RunStatus.SUCCESS,
                message=f"Successfully scraped {len(quote_elements)} quotes",
                metadata=meta.model_dump(),
            )
        except Exception as e:
            context.log("error", f"Extraction failed: {e}")
            return BotResult(
                status=RunStatus.FAILED,
                message=str(e),
            )
        finally:
            # 5. Always clean up browser session
            driver.quit()
```

#### Lifecycle & Context Contract

| Object / Method                 | Purpose                                                                                                                                                                           |
| :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `context.browser_mode`          | Runtime mode: `BrowserMode.HEADFUL` or `BrowserMode.HEADLESS`.                                                                                                                    |
| `context.update_metadata(dict)` | Atomically patches `runs.bot_metadata` in PostgreSQL in real time. Critical for saving challenge IDs or tokens mid-run before potential network failures or worker interruptions. |
| `context.log(event_type, msg)`  | Inserts a timestamped audit event into `run_events` table (rendered in Web UI modal).                                                                                             |
| `BotResult.status`              | Final run status: `RunStatus.SUCCESS`, `RunStatus.FAILED`, or `RunStatus.BLOCKED`.                                                                                                |
| `BotResult.message`             | Explanatory message. Set on `runs.error_message` for failed/blocked runs.                                                                                                         |
| `BotResult.metadata`            | Final metadata merged into `runs.bot_metadata`.                                                                                                                                   |

### Step 4: Register the Bot in the Platform Registry

In `backend/app/bots/registry.py`:

```python
from app.bots.implementations.quotes_bot import QuotesBot

registry.register(QuotesBot)
```

The platform handles the rest:

1. `GET /api/bots` returns `quotes_bot` in the bot catalog.
2. The Web Dashboard dropdown automatically displays **Quotes Scraper (`quotes_bot`)**.
3. Queue worker atomically claims and executes runs via `execute_run()`.
4. Run history, status, JSONB metadata, and audit events persist across container restarts.

## 4. Tests

### Inside Docker

```bash
docker compose exec api pytest -v
```

### Local with uv

```bash
cd backend
uv run pytest -v
```

Tests cover API endpoints, atomic queue claiming, crash recovery, JSONB metadata patching, Selenium remote connection, and `challenge_id` persistence across success and failure paths.

## 5. Anti-Bot Evasion Benchmark (Bonus)

Full reverse-engineering analysis, client-side detection vectors, and the empirical ablation study are documented in [`anti-bot-investigation.md`](anti-bot-investigation.md).

## 6. Data Persistence & Troubleshooting

- **Data Persistence:** PostgreSQL data is stored on named volume `pg_data`. Run records and event logs survive `docker compose down && docker compose up -d`.
- **Port Conflicts:** If `3000`, `8000`, `5434`, or `7900` are occupied, adjust port mappings in `docker-compose.yml`.
- **Worker Crash Recovery:** If the worker container restarts during execution, it automatically flags interrupted runs as `FAILED` on startup so they do not stay stuck in `RUNNING`.
