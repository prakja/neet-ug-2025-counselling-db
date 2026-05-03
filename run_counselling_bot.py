"""Entry point for the NEET Counselling Telegram Bot (polling mode).

Loads .env file from project root, then starts the bot.
"""

import os
import sys
import signal
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


ENV_PATH = Path(__file__).with_name(".env")
if ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        logger.info("Loaded env from %s", ENV_PATH)
    except ImportError:
        logger.warning("python-dotenv not installed, skipping .env load")
else:
    logger.warning(".env file not found at %s", ENV_PATH)


from counselling_bot.config import COUNSELLING_BOT_TOKEN
from counselling_bot.handlers import create_app


def main() -> None:
    token = COUNSELLING_BOT_TOKEN
    if not token:
        raise RuntimeError("COUNSELLING_BOT_TOKEN env var not set")

    if not os.getenv("DB_PASSWORD"):
        logger.warning("DB_PASSWORD not set – DB queries will fail")
    else:
        logger.info("DB config OK (host=%s, user=%s)",
                    os.getenv("DB_HOST", "default"),
                    os.getenv("DB_USER", "default"))

    logger.info("Initializing NEET Counselling Telegram Bot...")
    app = create_app(token)

    # Handle SIGTERM gracefully (ECS sends this before stopping task)
    def _signal_handler(signum, _frame):
        logger.info("Received signal %s, shutting down gracefully...", signum)
        try:
            app.stop()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Wait for any old bot instance to drop its Telegram connection.
    # ECS rolling deployments can briefly run two tasks with the same token,
    # causing "Conflict: terminated by other getUpdates request".
    startup_delay = int(os.getenv("BOT_STARTUP_DELAY_SECONDS", "5"))
    if startup_delay > 0:
        logger.info("Waiting %s seconds before polling to clear previous connection...", startup_delay)
        time.sleep(startup_delay)

    logger.info("Starting polling...")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
