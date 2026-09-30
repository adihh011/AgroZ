"""Live Indian mandi market integration with a safe demo fallback.

Agmarknet 2.0 exposes a public backend at api.agmarknet.gov.in/v1. The
integration first discovers commodity metadata and then attempts a public
last-week price endpoint. Because upstream schemas can change, parsing is
intentionally defensive. If the public endpoint is unavailable, the UI keeps
working and labels the values as demo data.
"""
import os
from datetime import date, timedelta
import requests

BASE_URL = "https://api.agmarknet.gov.in/v1"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://agmarknet.gov.in",
    "Referer": "https://agmarknet.gov.in/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/135 Safari/537.36",
}
BASE = {"rice": 3200, "maize": 2400, "banana": 2800, "potato": 2200, "tomato": 3000, "cotton": 7000, "chickpea": 6200, "mango": 4500}


def _request(path, params=None, method="get", json=None):
    r = requests.request(method, BASE_URL + path, params=params, json=json, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def _items(obj):
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        for k in ("data", "result", "results", "content", "records", "commodities"):
            v = obj.get(k)
            if isinstance(v, list): return v
    return []


def _find_commodity_id(name):
    data = _request("/daily-price-arrival/filters")
    items = _items(data)
    target = name.strip().lower()
    for item in items:
        if not isinstance(item, dict): continue
        label = str(item.get("name") or item.get("commodityName") or item.get("commodity") or item.get("label") or "").strip().lower()
        if label == target or target in label:
            return item.get("id") or item.get("commodityId") or item.get("commodity_id")
    return None


def _number(item, *keys):
    for k in keys:
        if isinstance(item, dict) and item.get(k) not in (None, ""):
            try: return float(str(item[k]).replace(",", ""))
            except ValueError: pass
    return None


def _parse_rows(payload, commodity):
    rows = _items(payload)
    parsed = []
    for row in rows:
        if not isinstance(row, dict): continue
        market = str(row.get("market") or row.get("marketName") or row.get("market_name") or row.get("mandi") or row.get("marketname") or "Market").strip()
        price = _number(row, "modalPrice", "modal_price", "modal", "maxPrice", "max_price", "price")
        if price is not None:
            parsed.append({"name": market, "price": round(price, 2)})
    return parsed[:12]


def get_market_data(commodity):
    live_enabled = os.environ.get("AGMARKNET_ENABLED", "true").lower() not in {"0", "false", "no"}
    if live_enabled:
        try:
            cid = _find_commodity_id(commodity)
            if cid:
                today = date.today().isoformat()
                payload = _request("/prices-and-arrivals/commodity-price/lastweek", params={"commodity": cid, "date": today})
                markets = _parse_rows(payload, commodity)
                if markets:
                    best = max(markets, key=lambda x: x["price"])
                    history = [{"date": today, "price": best["price"]}]
                    return {"live": True, "source": "AGMARKNET public market backend", "commodity": commodity.title(), "markets": markets, "history": history, "best_market": best["name"], "best_price": best["price"], "note": "Live market values retrieved from the public AGMARKNET backend."}
        except Exception:
            pass
    return demo_market_data(commodity)


def demo_market_data(commodity):
    key = commodity.lower()
    base = BASE.get(key, 2500)
    markets = ["Development Mandi", "Regional Market", "Wholesale Market"]
    values = [base, round(base * 1.08), round(base * 0.96)]
    today = date.today()
    history = [{"date": (today - timedelta(days=6-i)).isoformat(), "price": round(base * (0.94 + i * 0.012))} for i in range(7)]
    best_i = max(range(len(values)), key=lambda i: values[i])
    return {"live": False, "source": "Demo fallback — AGMARKNET was unavailable or returned no matching rows.", "commodity": commodity.title(), "markets": [{"name": markets[i], "price": values[i]} for i in range(3)], "history": history, "best_market": markets[best_i], "best_price": values[best_i], "note": "These are development placeholders, not live quotations."}
