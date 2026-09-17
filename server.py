from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
from bs4 import BeautifulSoup
import re
import time


# =========================================================
# XTrend Speed Signal Bot
# AUTO TRADE: OFF
# =========================================================

app = FastAPI(
    title="XTrend Speed Signal Bot",
    version="3.0"
)


# =========================================================
# SETTINGS
# =========================================================

XTrend_URL = "https://www.xtrendspeed.com/en-US/signal"

REFRESH_SECONDS = 30


# =========================================================
# STATIC FILES
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)


# =========================================================
# CACHE
# =========================================================

cache = {
    "signals": [],
    "updated_at": 0,
    "error": None
}


# =========================================================
# HTTP HEADERS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(iPhone; CPU iPhone OS 18_0 like Mac OS X) "
        "AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) "
        "Version/18.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# =========================================================
# SUPPORTED SYMBOLS
# =========================================================

SYMBOLS = [
    "AUDUSD",
    "EURUSD",
    "USDJPY",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "AUDJPY",
    "EURJPY",
    "GBPJPY",
    "XAUUSD",
    "USOIL",
    "US30",
    "NAS100",
    "SPX500",
]


# =========================================================
# PARSE XTREND PAGE
# =========================================================

def parse_signals(html: str):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    signals = []

    # Try table rows first
    rows = soup.find_all("tr")

    for row in rows:

        cells = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in row.find_all(
                ["td", "th"]
            )
        ]

        if not cells:
            continue

        row_text = " ".join(cells)

        symbol = None

        for item in SYMBOLS:
            if item in row_text.upper():
                symbol = item
                break

        if not symbol:
            continue

        # Direction
        direction = None

        if re.search(
            r"\bBUY\b",
            row_text,
            re.IGNORECASE
        ):
            direction = "BUY"

        elif re.search(
            r"\bSELL\b",
            row_text,
            re.IGNORECASE
        ):
            direction = "SELL"

        if not direction:
            continue

        # Strength
        if re.search(
            r"\bSTRONG\b",
            row_text,
            re.IGNORECASE
        ):
            strength = "STRONG"
        else:
            strength = "GENERAL"

        # Update time
        time_match = re.search(
            r"\b\d{1,2}:\d{2}\b",
            row_text
        )

        update_time = (
            time_match.group(0)
            if time_match
            else ""
        )

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "strength": strength,
            "update_time": update_time
        })

    return signals


# =========================================================
# DOWNLOAD XTREND DATA
# =========================================================

def fetch_signals():

    try:

        response = requests.get(
            XTrend_URL,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        signals = parse_signals(
            response.text
        )

        if not signals:

            return [], (
                "XTrend page loaded, "
                "but no signals could be parsed."
            )

        return signals, None

    except requests.HTTPError as error:

        return [], (
            f"XTrend server returned "
            f"HTTP {error.response.status_code}."
        )

    except requests.RequestException as error:

        return [], (
            f"Connection error: {error}"
        )

    except Exception as error:

        return [], (
            f"Unexpected error: {error}"
        )


# =========================================================
# HOME PAGE
# =========================================================

@app.get("/")
def home():

    return FileResponse(
        "app/static/index.html"
    )


# =========================================================
# MANIFEST
# =========================================================

@app.get("/manifest.webmanifest")
def manifest():

    return FileResponse(
        "app/static/manifest.webmanifest",
        media_type="application/manifest+json"
    )


# =========================================================
# SERVICE WORKER
# =========================================================

@app.get("/sw.js")
def service_worker():

    return FileResponse(
        "app/static/sw.js",
        media_type="application/javascript"
    )


# =========================================================
# SIGNAL API
# =========================================================

@app.get("/api/signals")
def get_signals():

    current_time = time.time()

    needs_refresh = (
        current_time - cache["updated_at"]
        >= REFRESH_SECONDS
        or not cache["signals"]
    )

    if needs_refresh:

        signals, error = fetch_signals()

        if signals:

            cache["signals"] = signals
            cache["updated_at"] = current_time
            cache["error"] = None

        else:

            cache["error"] = error

    # Live data available
    if cache["signals"]:

        return {
            "ok": True,
            "auto_trade": False,
            "source": XTrend_URL,
            "updated_at": cache["updated_at"],
            "signals": cache["signals"]
        }

    # Live data unavailable
    return {
        "ok": False,
        "auto_trade": False,
        "source": XTrend_URL,
        "updated_at": cache["updated_at"],
        "error": cache["error"],
        "signals": []
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "online",
        "bot": "XTrend Speed Signal Bot",
        "auto_trade": False
    }
