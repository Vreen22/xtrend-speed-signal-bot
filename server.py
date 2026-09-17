from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests,re,time
from bs4 import BeautifulSoup
URL="https://www.xtrendspeed.com/en-US/signal"
app=FastAPI(title="XTrend Speed Signal Bot")
app.mount("/static",StaticFiles(directory="app/static"),name="static")
cache={"ts":0,"signals":[]}
def scrape():
 r=requests.get(URL,headers={"User-Agent":"Mozilla/5.0"},timeout=15);r.raise_for_status()
 t=BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True); out=[]; seen=set()
 for s in re.findall(r'\b[A-Z]{6}\b',t):
  if s in seen: continue
  p=t.find(s); c=t[p:p+180]
  d="BUY" if re.search(r'\bBuy\b',c,re.I) else ("SELL" if re.search(r'\bSell\b',c,re.I) else None)
  if not d: continue
  st="STRONG" if re.search(r'\bStrong\b',c,re.I) else "GENERAL"
  tm=re.search(r'\b\d{1,2}:\d{2}\b',c)
  out.append({"symbol":s,"direction":d,"strength":st,"update_time":tm.group(0) if tm else ""});seen.add(s)
 return out
@app.get("/")
def home(): return FileResponse("app/static/index.html")
@app.get("/manifest.webmanifest")
def manifest(): return FileResponse("app/static/manifest.webmanifest",media_type="application/manifest+json")
@app.get("/sw.js")
def sw(): return FileResponse("app/static/sw.js",media_type="application/javascript")
@app.get("/api/signals")
def signals():
 if time.time()-cache["ts"]>30 or not cache["signals"]:
  try: cache["signals"]=scrape();cache["ts"]=time.time()
  except Exception as e: return {"ok":False,"source":URL,"error":str(e),"signals":cache["signals"]}
 return {"ok":True,"source":URL,"updated_at":cache["ts"],"signals":cache["signals"]}
