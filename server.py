from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
from bs4 import BeautifulSoup
import re
import time

app = FastAPI(title="XTrend Speed Signal Bot")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

XTREND_URLS = [
    "https://www.xtrendspeed.com/en-US/signal",
    "https://www.xtrendspeed.com/fr-FR/signal",
]

cache = {
    "signals": [],
    "updated_at": 0,
    "error": None
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_signals(html: str):
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ", strip=True)

    symbols = [
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

    signals = []
    seen = set()

    for symbol in symbols:
        if symbol in seen:
            continue

        position = text.find(symbol)

        if position == -1:
            continue

        section = text[position:position + 250]

        buy_match = re.search(r"\bBuy\b", section, re.I)
        sell_match = re.search(r"\bSell\b", section, re.I)

        if buy_match:
            direction = "BUY"
        elif sell_match:
            direction = "SELL"
        else:
            continue

        if re.search(r"\bStrong\b", section, re.I):
            strength = "STRONG"
        else:
            strength = "GENERAL"

        time_match = re.search(r"\b\d{1,2}:\d{2}\b", section)

        update_time = ""
        if time_match:
            update_time = time_match.group(0)

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "strength": strength,
            "update_time": update_time
        })

        seen.add(symbol)

    return signals


def fetch_signals():
    errors = []

    for url in XTREND_URLS:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=15
            )

            response.raise_for_status()

            signals = parse_signals(response.text)

            if signals:
                return signals, None

            errors.append(
                f"{url}: page loaded but no signals were parsed"
            )

        except Exception as e:
            errors.append(
                f"{url}: {str(e)}"
            )

    return [], " | ".join(errors)


@app.get("/")
def home():
    return FileResponse("app/static/index.html")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(
        "app/static/manifest.webmanifest",
        media_type="application/manifest+json"
    )


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        "app/static/sw.js",
        media_type="application/javascript"
    )


@app.get("/api/signals")
def signals():

    now = time.time()

    # Refresh every 30 seconds
    if (
        now - cache["updated_at"] > 30
        or not cache["signals"]
    ):
        new_signals, error = fetch_signals()

        if new_signals:
            cache["signals"] = new_signals
            cache["updated_at"] = now
            cache["error"] = None
        else:
            cache["error"] = error

    if cache["signals"]:
        return {
            "ok": True,
            "source": XTREND_URLS[0],
            "updated_at": cache["updated_at"],
            "signals": cache["signals"]
        }

    return {
        "ok": False,
        "source": XTREND_URLS[0],
        "updated_at": cache["updated_at"],
        "error": cache["error"],
        "signals": []
    }
