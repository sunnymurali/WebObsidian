"""
Run once — scrapes all accounts, pushes new clippings to GitHub, then exits.
Run this once a day when you turn on your PC.
"""

import logging
import re
import subprocess
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
            match = re.search(r'^tickers:\s*\[\s*\]', text, re.MULTILINE)
            if match:
                f.unlink()
                deleted += 1
                logger.debug("Deleted (no tickers): %s", f.name)
        except Exception as e:
            logger.error("Error checking %s: %s", f.name, e)
    logger.info("Deleted %d clipping(s) with no tickers", deleted)
    return deleted


def main():
    total = 0
    for account in ACCOUNTS:
        logger.info("── Scraping @%s ─────────────────────────────", account.handle)
        try:
            count = scrape(account)
            logger.info("── @%s done: %d new clipping(s)", account.handle, count)
            total += count
        except RuntimeError as e:
            logger.error("Setup required for @%s: %s", account.handle, e)
        except Exception as e:
            logger.error("Error scraping @%s: %s", account.handle, e)

    logger.info("────────────────────────────────────────────────")
    logger.info("Total new clippings: %d", total)

    cleanup_no_tickers()

    # Push to GitHub
    try:
        repo = str(DEFAULT_CLIPPINGS_DIR)
        subprocess.run(["git", "-C", repo, "add", "*.md"], check=True)
        result = subprocess.run(["git", "-C", repo, "diff", "--cached", "--quiet"])
        if result.returncode != 0:
            subprocess.run(["git", "-C", repo, "commit", "-m", f"Daily catch-up: {total} new clipping(s)"], check=True)
            subprocess.run(["git", "-C", repo, "push"], check=True)
            logger.info("Pushed to GitHub — VM will sync within 30 minutes")
        else:
            logger.info("No new clippings to push")
    except Exception as e:
        logger.error("Git push failed: %s", e)


if __name__ == "__main__":
    main()
