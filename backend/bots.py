from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
from datetime import datetime

from auth import get_current_user
from database import fetch_one, fetch_all, execute_db

router = APIRouter(prefix="/api/bots", tags=["bots"])

class BotCreate(BaseModel):
    name: str
    welcome_message: str
    theme_color: str = "#c6ff6d"

class BotOut(BaseModel):
    id: str
    name: str
    welcome_message: str
    theme_color: str
    created_at: str

@router.post("/", response_model=BotOut)
def create_bot(bot: BotCreate, current_user: dict = Depends(get_current_user)):
    bot_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    execute_db(
        "INSERT INTO bots (id, user_id, name, welcome_message, theme_color, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (bot_id, current_user["id"], bot.name, bot.welcome_message, bot.theme_color, created_at)
    )
    return fetch_one("SELECT * FROM bots WHERE id = ?", (bot_id,))

@router.get("/", response_model=List[BotOut])
def list_bots(current_user: dict = Depends(get_current_user)):
    return fetch_all("SELECT * FROM bots WHERE user_id = ?", (current_user["id"],))

@router.get("/{bot_id}", response_model=BotOut)
def get_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@router.put("/{bot_id}", response_model=BotOut)
def update_bot(bot_id: str, bot_update: BotCreate, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    execute_db(
        "UPDATE bots SET name = ?, welcome_message = ?, theme_color = ? WHERE id = ?",
        (bot_update.name, bot_update.welcome_message, bot_update.theme_color, bot_id)
    )
    return fetch_one("SELECT * FROM bots WHERE id = ?", (bot_id,))

@router.delete("/{bot_id}")
def delete_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    execute_db("DELETE FROM knowledge_sources WHERE bot_id = ?", (bot_id,))
    execute_db("DELETE FROM conversations WHERE bot_id = ?", (bot_id,))
    execute_db("DELETE FROM bots WHERE id = ?", (bot_id,))
    return {"status": "deleted"}
