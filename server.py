from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
import re
import time
from bs4 import BeautifulSoup

app = FastAPI(title="XTrend Speed Signal Bot")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

URLS = [
    "https://www.xtrendspeed.com/en-US/signal",
    "https://www.xtrendspeed.com/fr-FR/signal",
    "https://www.xtrendspeed.com/en-US/zh-cn/signal",
]

cache = {
    "ts": 0,
    "signals": []
}


def scrape_url(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.xtrendspeed.com/",
    }

    r = requests.get(
        url,
        headers=headers,
        timeout=20,
        allow_redirects=True
    )

    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    signals = []
    seen = set()

    symbols = re.findall(r"\b[A-Z]{6}\b", text)

    for symbol in symbols:
        if symbol in seen:
            continue

        pos = text.find(symbol)

        if pos == -1:
            continue

        section = text[pos:pos + 300]

        buy = re.search(r"\bBuy\b", section, re.I)
        sell = re.search(r"\bSell\b", section, re.I)

        if buy:
            direction = "BUY"
        elif sell:
            direction = "SELL"
        else:
            continue

        strong = re.search(r"\bStrong\b", section, re.I)

        strength = "STRONG" if strong else "GENERAL"

        tm = re.search(r"\b\d{1,2}:\d{2}\b", section)

        update_time = tm.group(0) if tm else ""

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "strength": strength,
            "update_time": update_time
        })

        seen.add(symbol)

    return signals


def scrape():
    last_error = None

    for url in URLS:
        try:
            data = scrape_url(url)

            if data:
                return data

        except Exception as e:
            last_error = str(e)

    if last_error:
        raise Exception(last_error)

    return []


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

    if time.time() - cache["ts"] > 30 or not cache["signals"]:

        try:
            data = scrape()

            if data:
                cache["signals"] = data
                cache["ts"] = time.time()

        except Exception as e:

            return {
                "ok": False,
                "source": URLS[0],
                "error": str(e),
                "signals": cache["signals"]
            }

    return {
        "ok": True,
        "source": URLS[0],
        "updated_at": cache["ts"],
        "signals": cache["signals"]
    }