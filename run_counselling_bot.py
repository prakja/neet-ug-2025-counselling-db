"""Entry point for the NEET Counselling Telegram Bot (polling mode).

Loads .env file from project root, then starts the bot.
"""

import os
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

    logger.info("Starting NEET Counselling Telegram Bot...")
    app = create_app(token)

    try:
        app.run_polling()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
