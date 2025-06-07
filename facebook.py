import time
import requests
from config import PIXEL_ID, ACCESS_TOKEN

def send_fb_event(telegram_id: int, ref: str):
    payload = {
        "data": [{
            "event_name": "Subscribe",
            "event_time": int(time.time()),
            "action_source": "chat",
            "user_data": {
                "subscription_id": str(telegram_id),
                "client_ip_address": "0.0.0.0",
                "client_user_agent": "telegram"
            },
            "custom_data": {
                "ref": ref
            },
            "event_id": f"{telegram_id}_{int(time.time())}"
        }]
    }
    r = requests.post(
        f"https://graph.facebook.com/v18.0/{PIXEL_ID}/events?access_token={ACCESS_TOKEN}",
        json=payload
    )
    print(f"[FB] Status: {r.status_code} | {r.text}")