from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import uuid
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from auth import get_current_user
from database import DB_PATH, fetch_one, fetch_all, execute_db
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


def normalize_source_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Enter a valid http or https website URL")
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def claim_source_scrape(bot_id: str, user_id: str, url: str, source_id: str | None = None) -> dict:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    now = datetime.utcnow()
    stale_before = (now - timedelta(minutes=30)).isoformat()
    try:
        connection.execute("BEGIN IMMEDIATE")
        bot = connection.execute(
            "SELECT id FROM bots WHERE id = ? AND user_id = ?", (bot_id, user_id)
        ).fetchone()
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        if source_id:
            source = connection.execute(
                "SELECT * FROM knowledge_sources WHERE id = ? AND bot_id = ?", (source_id, bot_id)
            ).fetchone()
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
            url = source["url"]
        else:
            normalized_url = normalize_source_url(url)
            existing_sources = connection.execute(
                "SELECT url FROM knowledge_sources WHERE bot_id = ?", (bot_id,)
            ).fetchall()
            if any(normalize_source_url(row["url"]) == normalized_url for row in existing_sources):
                raise HTTPException(
                    status_code=409,
                    detail="This website is already added. Use its Refresh button to update it.",
                )

        active = connection.execute(
            """
            SELECT knowledge_sources.id
            FROM knowledge_sources
            JOIN bots ON bots.id = knowledge_sources.bot_id
            WHERE bots.user_id = ? AND knowledge_sources.status = 'scraping'
              AND knowledge_sources.scrape_started_at > ?
              AND (? IS NULL OR knowledge_sources.id != ?)
            LIMIT 1
            """,
            (user_id, stale_before, source_id, source_id),
        ).fetchone()
        if active:
            raise HTTPException(
                status_code=409,
                detail="Another website is currently being scraped for this account. Please wait for it to finish.",
            )

        started_at = now.isoformat()
        if source_id:
            connection.execute(
                "UPDATE knowledge_sources SET status = 'scraping', pages_scraped = 0, scrape_started_at = ? WHERE id = ?",
                (started_at, source_id),
            )
            result = dict(source)
            result["status"] = "scraping"
            result["pages_scraped"] = 0
        else:
            source_id = str(uuid.uuid4())
            url = normalize_source_url(url)
            connection.execute(
                """
                INSERT INTO knowledge_sources (id, bot_id, url, status, pages_scraped, scrape_started_at, created_at)
                VALUES (?, ?, ?, 'scraping', 0, ?, ?)
                """,
                (source_id, bot_id, url, started_at, started_at),
            )
            result = dict(connection.execute(
                "SELECT * FROM knowledge_sources WHERE id = ?", (source_id,)
            ).fetchone())

        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


async def scrape_claimed_source(bot_id: str, source_id: str, url: str, refresh: bool = False) -> dict:
    async def report_progress(pages_scraped: int):
        execute_db("UPDATE knowledge_sources SET pages_scraped = ? WHERE id = ?", (pages_scraped, source_id))

    try:
        scraped_pages = await scrape_url(url, progress_callback=report_progress)
        if not scraped_pages:
            raise HTTPException(status_code=502, detail="The website could not be scraped")

        for page in scraped_pages:
            if refresh:
                delete_source_chunks(bot_id, page["url"])
            chunks = chunk_text(page["content"])
            add_chunks(bot_id, page["url"], chunks, page["title"])

        execute_db(
            "UPDATE knowledge_sources SET status = 'ready', pages_scraped = ?, scrape_started_at = NULL WHERE id = ?",
            (len(scraped_pages), source_id),
        )
    except HTTPException:
        execute_db("UPDATE knowledge_sources SET status = 'failed', scrape_started_at = NULL WHERE id = ?", (source_id,))
        raise
    except Exception as error:
        execute_db("UPDATE knowledge_sources SET status = 'failed', scrape_started_at = NULL WHERE id = ?", (source_id,))
        print(f"Source scrape error for {source_id}: {error}")
        raise HTTPException(status_code=502, detail="The website could not be scraped") from error

    return fetch_one("SELECT * FROM knowledge_sources WHERE id = ?", (source_id,))


@router.post("/{bot_id}/sources", response_model=SourceOut)
async def add_source(bot_id: str, source: SourceCreate, current_user: dict = Depends(get_current_user)):
    source = claim_source_scrape(bot_id, current_user["id"], source.url)
    return await scrape_claimed_source(bot_id, source["id"], source["url"])

@router.get("/{bot_id}/sources", response_model=List[SourceOut])
def list_sources(bot_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return fetch_all("SELECT * FROM knowledge_sources WHERE bot_id = ?", (bot_id,))


@router.post("/{bot_id}/sources/{source_id}/refresh", response_model=SourceOut)
async def refresh_source(bot_id: str, source_id: str, current_user: dict = Depends(get_current_user)):
    source = claim_source_scrape(bot_id, current_user["id"], "", source_id)
    return await scrape_claimed_source(bot_id, source_id, source["url"], refresh=True)


@router.delete("/{bot_id}/sources/{source_id}")
def delete_source(bot_id: str, source_id: str, current_user: dict = Depends(get_current_user)):
    bot = fetch_one("SELECT * FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user["id"]))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
        
    source = fetch_one("SELECT * FROM knowledge_sources WHERE id = ? AND bot_id = ?", (source_id, bot_id))
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source["status"] == "scraping":
        raise HTTPException(status_code=409, detail="Wait for the current scrape to finish before deleting this source")
        
    delete_source_chunks(bot_id, source["url"])
    execute_db("DELETE FROM knowledge_sources WHERE id = ?", (source_id,))
    
    return {"status": "deleted"}
