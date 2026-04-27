"""
Scrapes all configured accounts and saves Obsidian clippings.
Runs immediately on start, then every 30 minutes.
"""

import logging
import re
import subprocess
import time

import schedule

from config import ACCOUNTS, DEFAULT_CLIPPINGS_DIR
from scraper import scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def cleanup_no_tickers():
    deleted = 0
    for f in DEFAULT_CLIPPINGS_DIR.glob("tweet_*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            if re.search(r'^tickers:\s*\[\s*\]', text, re.MULTILINE):
                f.unlink()
                deleted += 1
        except Exception as e:
            logger.error("Error checking %s: %s", f.name, e)
    logger.info("Deleted %d clipping(s) with no tickers", deleted)


def push_clippings():
    try:
        repo = str(DEFAULT_CLIPPINGS_DIR)
        subprocess.run(["git", "-C", repo, "add", "*.md"], check=True)
        result = subprocess.run(["git", "-C", repo, "diff", "--cached", "--quiet"])
        if result.returncode != 0:
            subprocess.run(["git", "-C", repo, "commit", "-m", "New clippings"], check=True)
            subprocess.run(["git", "-C", repo, "push"], check=True)
            logger.info("Clippings pushed to GitHub")
        else:
            logger.info("No new clippings to push")
    except Exception as e:
        logger.error("Git push failed: %s", e)


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
    cleanup_no_tickers()
    push_clippings()


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
