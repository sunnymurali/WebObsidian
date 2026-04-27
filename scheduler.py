"""
Scrapes all configured accounts and saves Obsidian clippings.
Runs immediately on start, then every 30 minutes.
"""

import logging
import time

import schedule

from config import ACCOUNTS
from scraper import scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_all():
    for account in ACCOUNTS:
        logger.info("── Scraping @%s ─────────────────────────────", account.handle)
        try:
            count = scrape(account)
            logger.info("── @%s done: %d new clipping(s) ────────────", account.handle, count)
        except RuntimeError as e:
            logger.error("Setup required for @%s: %s", account.handle, e)
        except Exception as e:
            logger.error("Error scraping @%s: %s", account.handle, e)


if __name__ == "__main__":
    handles = ", ".join(f"@{a.handle}" for a in ACCOUNTS)
    logger.info("WebObsidian scheduler started (every 30 minutes)")
    logger.info("Tracking: %s", handles)
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    run_all()

    schedule.every(30).minutes.do(run_all)

    while True:
        schedule.run_pending()
        time.sleep(30)
