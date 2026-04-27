from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

X_BASE_URL = "https://x.com"

# Default directory for all accounts unless overridden per account
DEFAULT_CLIPPINGS_DIR = Path(r"C:\Users\Sunny\Downloads\InvestmentWiki\Clippings")


@dataclass
class AccountConfig:
    handle: str
    place: str = "posts"        # "posts" → main profile timeline
                                # "subs"  → creator subscriptions feed
    max_tweets: int = 55
    clippings_dir: Optional[Path] = None  # None uses DEFAULT_CLIPPINGS_DIR

    @property
    def resolved_clippings_dir(self) -> Path:
        return self.clippings_dir or DEFAULT_CLIPPINGS_DIR

    @property
    def target_url(self) -> str:
        base = f"{X_BASE_URL}/{self.handle}"
        return f"{base}/creator-subscriptions" if self.place == "subs" else base


# ── Add or remove accounts here ──────────────────────────────────
ACCOUNTS: list[AccountConfig] = [
    AccountConfig(handle="OptionsHawk",      place="posts"),
    AccountConfig(handle="3PeaksTrading",    place="posts"),
    AccountConfig(handle="investwithrules",  place="posts"),
    AccountConfig(handle="LeifSoreide",      place="posts"),
    AccountConfig(handle="FrankCappelleri",  place="posts"),
]
