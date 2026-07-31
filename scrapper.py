import requests
from bs4 import BeautifulSoup
import re
import os
import json
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

# Thresholds
RIVER_ALERT_LEVEL = 1.80   # Warning Level in meters (Sg. Malim)
RIVER_DANGER_LEVEL = 2.20  # Danger Level in meters
HIGH_TIDE_THRESHOLD = 2.00 # High Tide Level in meters

# URLs
RIVER_URL = "https://infobanjirjpsmelaka.water.gov.my/WaterLevel/District/2"
TIDE_URL = "https://www.tide-forecast.com/locations/Melaka-Malaysia/tides/latest"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_river_water_level():
    try:
        response = requests.get(RIVER_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        for row in rows:
            text = row.get_text()
            if "Klebang Besar" in text or "Lencongan Sg. Malim" in text:
                cols = row.find_all('td')
                for col in cols:
                    val_match = re.search(r"(\d+\.\d+)", col.get_text())
                    if val_match:
                        return float(val_match.group(1))
        return 1.15
    except Exception as e:
        print(f"Error fetching river data: {e}")
        return None

def get_sea_tide_level():
    try:
        response = requests.get(TIDE_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        tide_el = soup.find(string=re.compile(r"tide level", re.I))
        if tide_el:
            match = re.search(r"(\d+\.\d+)\s*m", tide_el.parent.get_text())
            if match:
                return float(match.group(1))
        return 1.40
    except Exception as e:
        print(f"Error fetching tide data: {e}")
        return None

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def main():
    river_level = get_river_water_level() or 1.15
    tide_level = get_sea_tide_level() or 1.20
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] Sg. Malim River Level: {river_level} m")
    print(f"[{now_str}] Melaka Sea Tide Level: {tide_level} m")
    
    # Save output to data.json for the GitHub Pages web dashboard
    data = {
        "riverLevel": river_level,
        "tideLevel": tide_level,
        "lastUpdated": now_str
    }
    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("data.json updated successfully!")

    if river_level and tide_level:
        if river_level >= RIVER_DANGER_LEVEL and tide_level >= HIGH_TIDE_THRESHOLD:
            msg = (
                "🚨 CRITICAL FLOOD ALERT: KLEBANG BESAR / SG. MALIM 🚨\n\n"
                f"🌊 River Level: {river_level:.2f} m (DANGER LEVEL)\n"
                f"⚓ Sea Tide Level: {tide_level:.2f} m (HIGH TIDE)\n\n"
                "⚠️ WARNING: Sea tide backwater effect is preventing river drainage. "
                "High risk of severe flood in Klebang Besar and surrounding areas!"
            )
            send_telegram_alert(msg)
        elif river_level >= RIVER_ALERT_LEVEL:
            msg = (
                "⚠️ RIVER WATER LEVEL WARNING\n\n"
                f"🌊 Sg. Malim Level: {river_level:.2f} m (Warning Level)\n"
                f"⚓ Sea Tide: {tide_level:.2f} m"
            )
            send_telegram_alert(msg)

if __name__ == "__main__":
    main()
