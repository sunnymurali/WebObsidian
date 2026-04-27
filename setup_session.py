"""
Extracts X/Twitter cookies from your real Chrome browser.
No login automation — just reads the session you already have.
Requires you to already be logged into x.com in Chrome.
"""

import json
from pathlib import Path

COOKIES_FILE = Path(__file__).parent / "x_cookies.json"


def setup():
    print("=" * 60)
    print("  WebObsidian — Cookie Setup")
    print("=" * 60)
    print()
    print("Make sure you are logged into x.com in Chrome first.")
    print()

    try:
        import browser_cookie3

        print("Reading cookies from Chrome...")
        jar = browser_cookie3.chrome(domain_name=".x.com")
        cookies = [
            {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "secure": bool(c.secure),
                "httpOnly": False,
                "sameSite": "Lax",
            }
            for c in jar
            if c.value  # skip empty values
        ]

        if not cookies:
            raise ValueError("No X/Twitter cookies found in Chrome.")

        COOKIES_FILE.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        print(f"Done — {len(cookies)} cookies saved to {COOKIES_FILE.name}")
        print()
        print("You can now run:  python scheduler.py")

    except Exception as e:
        print(f"Auto-extract failed: {e}")
        print()
        _manual_instructions()


def _manual_instructions():
    print("Manual fallback (2 minutes):")
    print()
    print("  1. Install 'Cookie-Editor' extension in Chrome")
    print("     https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm")
    print()
    print("  2. Go to https://x.com (make sure you are logged in)")
    print()
    print("  3. Click the Cookie-Editor icon → Export → Export as JSON")
    print()
    print(f"  4. Save the file as:  {COOKIES_FILE}")
    print()
    print("  5. Run:  python scheduler.py")


if __name__ == "__main__":
    setup()
