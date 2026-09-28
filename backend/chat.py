from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import uuid
import json
from datetime import datetime
from typing import List

from database import fetch_one, execute_db, fetch_all
from vector_store import query_chunks
from auth import get_current_user

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    visitor_id: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

@router.post("/api/chat/{bot_id}", response_model=ChatResponse)
def chat_with_bot(bot_id: str, req: ChatRequest):
    bot = fetch_one("SELECT * FROM bots WHERE id = ?", (bot_id,))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    chunks = query_chunks(bot_id, req.message, top_k=3)
    
    if not chunks:
        answer = "I'm sorry, I don't have enough information to answer that."
        sources = []
    else:
        # Simple MVP: use the best chunk
        best_chunk = chunks[0]
        answer = best_chunk["text"]
        sources = list(set([c["source"] for c in chunks]))
        
    # Store conversation
    convo_id = str(uuid.uuid4())
    msg_data = json.dumps([
        {"role": "user", "content": req.message},
        {"role": "bot", "content": answer, "sources": sources}
    ])
    
    execute_db(
        "INSERT INTO conversations (id, bot_id, visitor_id, messages, created_at) VALUES (?, ?, ?, ?, ?)",
        (convo_id, bot_id, req.visitor_id, msg_data, datetime.utcnow().isoformat())
    )
    
    return {"answer": answer, "sources": sources}

@router.get("/api/bots/{bot_id}/conversations")
def get_conversations(bot_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    convos = fetch_all("SELECT * FROM conversations WHERE bot_id = ? ORDER BY created_at DESC", (bot_id,))
    return convos
