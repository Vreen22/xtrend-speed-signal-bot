from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
import re
import time
from bs4 import BeautifulSoup

app = FastAPI(title="XTrend Speed Signal Bot")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# XTrend signal sources
URLS = [
    "https://speedwwwtest.xtrendspeed.com/en-US/signal",
    "https://www.xtrendspeed.com/en-US/signal",
    "https://www.xtrendspeed.com/fr-FR/signal",
]

cache = {
    "ts": 0,
    "signals": []
}


def scrape_url(url):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.xtrendspeed.com/",
        "Connection": "keep-alive",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20,
        allow_redirects=True
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text(" ", strip=True)

    signals = []
    seen = set()

    # XTrend symbols such as AUDUSD, EURUSD, USDJPY
    symbols = re.findall(r"\b[A-Z]{6}\b", text)

    for symbol in symbols:

        if symbol in seen:
            continue

        position = text.find(symbol)

        if position < 0:
            continue

        section = text[position:position + 250]

        # Direction
        if re.search(r"\bBuy\b", section, re.IGNORECASE):
            direction = "BUY"

        elif re.search(r"\bSell\b", section, re.IGNORECASE):
            direction = "SELL"

        else:
            continue

        # Strength
        if re.search(r"\bStrong\b", section, re.IGNORECASE):
            strength = "STRONG"
        else:
            strength = "GENERAL"

        # Update time
        time_match = re.search(
            r"\b\d{1,2}:\d{2}\b",
            section
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

        seen.add(symbol)

    return signals


def scrape():

    errors = []

    for url in URLS:

        try:

            data = scrape_url(url)

            if data:
                return data

        except Exception as error:

            errors.append(
                f"{url} -> {error}"
            )

    raise Exception(
        "All XTrend sources failed: "
        + " | ".join(errors)
    )


@app.get("/")
def home():

    return FileResponse(
        "app/static/index.html"
    )


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

    # Refresh every 30 seconds
    if (
        time.time() - cache["ts"] > 30
        or not cache["signals"]
    ):

        try:

            data = scrape()

            if data:

                cache["signals"] = data
                cache["ts"] = time.time()

        except Exception as error:

            return {
                "ok": False,
                "source": URLS[0],
                "error": str(error),
                "signals": cache["signals"]
            }

    return {
        "ok": True,
        "source": URLS[0],
        "updated_at": cache["ts"],
        "signals": cache["signals"]
    }