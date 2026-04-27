"""
Scrapes @OptionsHawk tweets and saves them as Obsidian MD clippings.
Uses cookies extracted from your real Chrome session — no login automation.
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import AccountConfig, ACCOUNTS, X_BASE_URL

COOKIES_FILE = Path(__file__).parent / "x_cookies.json"

REAL_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Common acronyms that look like tickers but aren't
NON_TICKERS = {
    # Exchanges & markets
    "NYSE", "NASDAQ", "AMEX", "OTC", "CME", "CBOE",
    # Instrument types
    "ETF", "IPO", "SPO", "SPAC",
    # Regulators & bodies
    "SEC", "CFTC", "FINRA", "FED", "FOMC", "IMF", "ECB",
    # Macro indicators
    "GDP", "CPI", "PPI", "PCE", "PMI", "ISM",
    # Financial terms
    "EPS", "PE", "PEG", "ROE", "ROA", "DCF", "FCF", "EBITDA",
    # Options / trading
    "ATM", "ITM", "OTM", "IV", "VIX", "DTE",
    # Time / calendar
    "AM", "PM", "EST", "PST", "CST", "UTC", "EOD", "EOM",
    "Q1", "Q2", "Q3", "Q4", "YTD", "QTD", "YOY",
    # Currencies
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD",
    # Titles / roles
    "CEO", "CFO", "COO", "CTO", "CFO",
    # Common words that appear in ALL CAPS
    "USA", "US", "UK", "EU", "AI", "IT", "OR", "AND", "FOR",
    "NOT", "ALL", "NEW", "TOP", "NOW", "THE", "BIG",
}


def extract_tickers(text: str) -> list[str]:
    """
    Extract stock tickers using two patterns:
      1. $AAPL  — dollar-sign prefix (always treated as ticker)
      2. (ETN)  — uppercase letters in parentheses, validated against ticker rules
    Ticker rules for bracket format: letters only, 1–5 chars, not a known acronym.
    """
    # $TICKER — dollar prefix, trust it as-is
    dollar = re.findall(r'\$([A-Z]{1,5})', text)

    # (TICKER) — all-uppercase, letters only, 1–5 chars, not a known non-ticker
    raw_parens = re.findall(r'\(([A-Z]{1,5})\)', text)
    parens = [
        t for t in raw_parens
        if t.isalpha()           # letters only — no numbers
        and t not in NON_TICKERS
    ]

    return sorted(set(dollar + parens))


def tweet_id_from_href(href: str) -> str:
    match = re.search(r'/status/(\d+)', href)
    return match.group(1) if match else ""


def clipping_path(tweet_id: str, clippings_dir: Path) -> Path:
    return clippings_dir / f"tweet_{tweet_id}.md"


def already_saved(tweet_id: str, clippings_dir: Path) -> bool:
    return clipping_path(tweet_id, clippings_dir).exists()


def save_clipping(tweet_id: str, text: str, url: str,
                  timestamp: str, tickers: list[str],
                  clippings_dir: Path, author: str) -> Path:
    clippings_dir.mkdir(parents=True, exist_ok=True)

    tickers_yaml = f"[{', '.join(tickers)}]" if tickers else "[]"
    date_str = (timestamp[:19].replace("T", " ")
                if timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_title = text[:80].replace('"', "'")

    content = (
        f'---\n'
        f'title: "{safe_title}"\n'
        f'source: {url}\n'
        f'author: "@{author}"\n'
        f'date: {date_str}\n'
        f'tickers: {tickers_yaml}\n'
        f'tags: [stocks, twitter, options]\n'
        f'scraped_at: {scraped_at}\n'
        f'---\n\n'
        f'{text}\n'
    )

    path = clipping_path(tweet_id, clippings_dir)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

def scrape(account: AccountConfig = None) -> int:
    if account is None:
        account = ACCOUNTS[0]

    TARGET_ACCOUNT = account.handle
    CLIPPINGS_DIR = account.resolved_clippings_dir
    MAX_TWEETS = account.max_tweets

    if not COOKIES_FILE.exists():
        raise RuntimeError(
            "No x_cookies.json found. Run setup_session.py first."
        )

    cookies = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    saved_count = 0
    seen_ids: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
            ignore_default_args=["--enable-automation"],
        )
        context = browser.new_context(
            user_agent=REAL_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )

        # Normalise sameSite values to what Playwright accepts
        SAME_SITE_MAP = {
            "strict": "Strict",
            "lax": "Lax",
            "none": "None",
            "no_restriction": "None",
            "unspecified": "Lax",
        }
        for c in cookies:
            raw = str(c.get("sameSite", "")).lower()
            c["sameSite"] = SAME_SITE_MAP.get(raw, "Lax")

        # Inject real Chrome cookies — bypasses login entirely
        context.add_cookies(cookies)

        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        logger.info("Navigating to %s/%s", TARGET_ACCOUNT, account.place)

        try:
            page.goto(account.target_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
        except PWTimeout:
            logger.error("Page load timed out for @%s", TARGET_ACCOUNT)
            browser.close()
            return 0

        # Check if cookies are still valid
        if "/login" in page.url or "/signup" in page.url:
            logger.error(
                "Cookies expired — run setup_session.py again to refresh them."
            )
            browser.close()
            return 0

        # For subs, verify we landed on the right page
        if account.place == "subs" and "creator-subscriptions" not in page.url:
            logger.error(
                "@%s place='subs' but redirected to %s — "
                "check subscription access or change to place='posts'.",
                TARGET_ACCOUNT, page.url,
            )
            browser.close()
            return 0

        scroll_attempts = 0
        max_scrolls = 25

        while len(seen_ids) < MAX_TWEETS and scroll_attempts < max_scrolls:
            articles = page.query_selector_all('article[data-testid="tweet"]')

            for article in articles:
                link = article.query_selector('a[href*="/status/"]')
                if not link:
                    continue
                href = link.get_attribute("href") or ""
                tweet_id = tweet_id_from_href(href)
                if not tweet_id or tweet_id in seen_ids:
                    continue
                seen_ids.add(tweet_id)

                if already_saved(tweet_id, CLIPPINGS_DIR):
                    logger.debug("Already saved: %s", tweet_id)
                    continue

                text_el = article.query_selector('div[data-testid="tweetText"]')
                if not text_el:
                    continue
                text = text_el.inner_text().strip()
                if not text:
                    continue

                time_el = article.query_selector("time")
                timestamp = (time_el.get_attribute("datetime") or ""
                             if time_el else "")

                full_url = f"{X_BASE_URL}{href}"
                tickers = extract_tickers(text)

                path = save_clipping(tweet_id, text, full_url, timestamp, tickers, CLIPPINGS_DIR, TARGET_ACCOUNT)
                saved_count += 1
                logger.info("Saved %-28s | tickers: %s",
                            path.name, tickers if tickers else "none")

            if len(seen_ids) >= MAX_TWEETS:
                break

            page.evaluate("window.scrollBy(0, 1200)")
            page.wait_for_timeout(2000)
            scroll_attempts += 1

        context.close()
        browser.close()
        logger.info("Browser closed")

    logger.info("Scrape complete — %d new clipping(s) saved", saved_count)
    return saved_count
