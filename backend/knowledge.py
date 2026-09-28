from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
from datetime import datetime

from auth import get_current_user
from database import fetch_one, fetch_all, execute_db
from scraper import scrape_url, chunk_text
from vector_store import add_chunks, delete_source_chunks

router = APIRouter(prefix="/api/bots", tags=["knowledge"])

class SourceCreate(BaseModel):
    url: str

class SourceOut(BaseModel):
    id: str
    bot_id: str
    url: str
    status: str
    pages_scraped: int
    created_at: str

@router.post("/{bot_id}/sources", response_model=SourceOut)
async def add_source(bot_id: str, source: SourceCreate, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    source_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    
    execute_db(
        "INSERT INTO knowledge_sources (id, bot_id, url, status, created_at) VALUES (?, ?, ?, 'scraping', ?)",
        (source_id, bot_id, source.url, created_at)
    )
    
    # Scrape synchronously for MVP
    scraped_pages = await scrape_url(source.url)
    
    for page in scraped_pages:
        chunks = chunk_text(page["content"])
        add_chunks(bot_id, page["url"], chunks, page["title"])
        
    execute_db(
        "UPDATE knowledge_sources SET status = 'ready', pages_scraped = ? WHERE id = ?",
        (len(scraped_pages), source_id)
    )
    
    return fetch_one("SELECT * FROM knowledge_sources WHERE id = ?", (source_id,))

@router.get("/{bot_id}/sources", response_model=List[SourceOut])
def list_sources(bot_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return fetch_all("SELECT * FROM knowledge_sources WHERE bot_id = ?", (bot_id,))

@router.delete("/{bot_id}/sources/{source_id}")
def delete_source(bot_id: str, source_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    source = fetch_one("SELECT * FROM knowledge_sources WHERE id = ? AND bot_id = ?", (source_id, bot_id))
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    delete_source_chunks(bot_id, source["url"])
    execute_db("DELETE FROM knowledge_sources WHERE id = ?", (source_id,))
    
    return {"status": "deleted"}
