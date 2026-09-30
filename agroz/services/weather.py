import os
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load local .env for development. On Render, environment variables are used directly.
load_dotenv()


def get_weather(location, crop=""):
    if not location:
        return {"live": False, "message": "Add a farm location in Profile to enable live weather.", "forecast": [], "alerts": []}
    owm_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not owm_key:
        return demo_weather(location)
    try:
        params = {"q": location, "appid": owm_key, "units": "metric"}
        current = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=8)
        current.raise_for_status()
        c = current.json()
        forecast = requests.get("https://api.openweathermap.org/data/2.5/forecast", params=params, timeout=8)
        forecast.raise_for_status()
        f = forecast.json()
        items = []
        for x in f.get("list", []):
            local = datetime.fromtimestamp(x["dt"])
            if local.hour in (12, 15, 18) and len(items) < 5:
                items.append({"date": local.strftime("%a"), "temp": round(x["main"]["temp"]), "rain": round(x.get("rain", {}).get("3h", 0), 1), "description": x["weather"][0]["description"].title()})
        if len(items) < 5:
            for x in f.get("list", [])[::8][:5-len(items)]:
                local = datetime.fromtimestamp(x["dt"])
                items.append({"date": local.strftime("%a"), "temp": round(x["main"]["temp"]), "rain": round(x.get("rain", {}).get("3h", 0), 1), "description": x["weather"][0]["description"].title()})
        temp = c["main"]["temp"]
        alerts = []
        if temp >= 35: alerts.append({"type": "Heat", "severity": "high", "message": "High temperature detected. Review irrigation and crop-stress precautions."})
        if any(x["rain"] >= 15 for x in items): alerts.append({"type": "Rain", "severity": "medium", "message": "Heavy rainfall is present in the forecast. Review field operations and harvest timing."})
        return {"live": True, "location": c.get("name", location), "temperature": round(temp), "humidity": c["main"]["humidity"], "wind": round(c["wind"]["speed"], 1), "description": c["weather"][0]["description"].title(), "forecast": items, "alerts": alerts}
    except Exception:
        demo = demo_weather(location)
        demo["message"] = "Live weather could not be reached. Check the API key, location and network."
        return demo


def demo_weather(location):
    return {"live": False, "location": location, "temperature": 29, "humidity": 76, "wind": 3.2, "description": "Partly Cloudy (Demo)", "forecast": [{"date":"Today","temp":29,"rain":2,"description":"Partly Cloudy"},{"date":"Tue","temp":30,"rain":8,"description":"Light Rain"},{"date":"Wed","temp":28,"rain":18,"description":"Rain"},{"date":"Thu","temp":29,"rain":5,"description":"Cloudy"},{"date":"Fri","temp":31,"rain":1,"description":"Clear"}], "alerts":[{"type":"Demo","severity":"info","message":"Add OPENWEATHER_API_KEY to switch this panel to live data."}]}
