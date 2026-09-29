from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, fetch_one
import auth
import bots
import knowledge
import chat

app = FastAPI(title="BroChat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(auth.router)
app.include_router(bots.router)
app.include_router(knowledge.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"status": "Brochat backend is running"}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

from fastapi.responses import FileResponse
from pathlib import Path

WIDGET_PATH = Path(__file__).parent.parent / "widget" / "brochat-widget.js"

@app.get("/widget.js")
def get_widget():
    if not WIDGET_PATH.exists():
        raise HTTPException(status_code=404, detail="Widget script not found")
    return FileResponse(str(WIDGET_PATH), media_type="application/javascript")

@app.get("/api/bots/{bot_id}/widget-config")
def widget_config(bot_id: str):
    bot = fetch_one("SELECT name, welcome_message, theme_color FROM bots WHERE id = ?", (bot_id,))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return dict(bot)
