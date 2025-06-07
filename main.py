import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from aiogram import types
import uvicorn

from config import BOT_TOKEN, BASE_URL, CHANNEL_ID
from bot_logic import bot, dp
from facebook import send_fb_event
from database import init_db, InviteLink, VisitStats

app = FastAPI()

@app.get("/")
def index():
    return {"msg": "Bot is live"}

@app.get("/landing")
async def serve_landing(ref: str = "default"):
    await VisitStats.create(ref=ref, visited=True)
    return FileResponse("landing.html", media_type="text/html")

@app.post("/clicked")
async def clicked_button(request: Request):
    data = await request.json()
    ref = data.get("ref", "default")
    await VisitStats.create(ref=ref, clicked=True)
    return JSONResponse({"ok": True})

@app.get("/get_invite")
async def get_invite(ref: str = "default"):
    existing = await InviteLink.get_or_none(ref=ref)
    if existing:
        return {"link": existing.link}
    
    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        name=ref,
        creates_join_request=True
    )
    await InviteLink.create(ref=ref, link=invite.invite_link)
    return {"link": invite.invite_link}

@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    raw_data = await request.body()
    update = types.Update.model_validate_json(raw_data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def set_webhook():
    await init_db()
    import requests
    res = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": f"{BASE_URL}/webhook/{BOT_TOKEN}"}
    )
    print(f"[WEBHOOK] set: {res.status_code} {res.text}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)