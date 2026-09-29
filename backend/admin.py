import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request

from auth import pwd_context, require_admin
from database import connect_database, execute_db, fetch_all, fetch_one
from vector_store import delete_bot_knowledge, restore_vector_documents

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class BotUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    welcome_message: str = Field(min_length=1, max_length=2000)
    theme_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


@router.post("/restore")
async def restore_backup(request: Request):
    payload = await request.body()
    if len(payload) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Backup file must be smaller than 20 MB")
    try:
        backup = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid backup JSON") from error
    if backup.get("format") != "brochat-backup" or backup.get("version") != 1:
        raise HTTPException(status_code=400, detail="Unsupported backup format")

    users = backup.get("users", [])
    bots = backup.get("bots", [])
    sources = backup.get("knowledge_sources", [])
    conversations = backup.get("conversations", [])
    vector_collections = backup.get("vector_collections", [])
    if any(not isinstance(items, list) for items in (users, bots, sources, conversations, vector_collections)):
        raise HTTPException(status_code=400, detail="Backup sections must be arrays")

    restored = {"users": 0, "bots": 0, "sources": 0, "conversations": 0, "vector_documents": 0}
    user_id_map = {}
    connection = connect_database()
    try:
        connection.execute("BEGIN")
        for user in users:
            old_id = str(user.get("id", ""))
            email = str(user.get("email", "")).strip()
            password_hash = str(user.get("password_hash", ""))
            if not old_id or not email or not password_hash:
                continue
            existing = connection.execute("SELECT id FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
            target_id = existing["id"] if existing else old_id
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO users (id, name, email, password_hash, role, auth_version, created_at)
                VALUES (?, ?, ?, ?, 'user', 0, ?)
                """,
                (target_id, str(user.get("name", "")), email, password_hash, user.get("created_at")),
            )
            restored["users"] += max(cursor.rowcount, 0)
            user_id_map[old_id] = target_id

        for bot in bots:
            bot_id = str(bot.get("id", ""))
            owner_id = user_id_map.get(str(bot.get("user_id", "")), str(bot.get("user_id", "")))
            if not bot_id or not connection.execute("SELECT id FROM users WHERE id = ?", (owner_id,)).fetchone():
                continue
            cursor = connection.execute(
                "INSERT OR IGNORE INTO bots (id, user_id, name, welcome_message, theme_color, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (bot_id, owner_id, bot.get("name", ""), bot.get("welcome_message", ""), bot.get("theme_color", "#c6ff6d"), bot.get("created_at")),
            )
            restored["bots"] += max(cursor.rowcount, 0)

        for source in sources:
            if not connection.execute("SELECT id FROM bots WHERE id = ?", (source.get("bot_id"),)).fetchone():
                continue
            cursor = connection.execute(
                "INSERT OR IGNORE INTO knowledge_sources (id, bot_id, url, status, pages_scraped, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (source.get("id"), source.get("bot_id"), source.get("url"), source.get("status", "ready"), source.get("pages_scraped", 0), source.get("created_at")),
            )
            restored["sources"] += max(cursor.rowcount, 0)

        for conversation in conversations:
            if not connection.execute("SELECT id FROM bots WHERE id = ?", (conversation.get("bot_id"),)).fetchone():
                continue
            cursor = connection.execute(
                "INSERT OR IGNORE INTO conversations (id, bot_id, visitor_id, messages, created_at) VALUES (?, ?, ?, ?, ?)",
                (conversation.get("id"), conversation.get("bot_id"), conversation.get("visitor_id", ""), conversation.get("messages", "[]"), conversation.get("created_at")),
            )
            restored["conversations"] += max(cursor.rowcount, 0)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    for collection_data in vector_collections:
        bot_id = str(collection_data.get("bot_id", ""))
        ids = collection_data.get("ids", [])
        documents = collection_data.get("documents", [])
        metadatas = collection_data.get("metadatas", [])
        embeddings = collection_data.get("embeddings")
        if not bot_id or not ids or not (len(ids) == len(documents) == len(metadatas)):
            continue
        if not fetch_one("SELECT id FROM bots WHERE id = ?", (bot_id,)):
            continue
        restored["vector_documents"] += restore_vector_documents(
            bot_id, ids, documents, metadatas, embeddings
        )

    return {"status": "merged", "restored": restored}


@router.get("/users")
def list_users():
    return fetch_all(
        """
        SELECT users.id, users.name, users.email, users.role, users.created_at,
               COUNT(bots.id) AS bot_count
        FROM users
        LEFT JOIN bots ON bots.user_id = users.id
        GROUP BY users.id
        ORDER BY users.created_at DESC
        """
    )


@router.get("/users/{user_id}/bots")
def list_user_bots(user_id: str):
    if not fetch_one("SELECT id FROM users WHERE id = ?", (user_id,)):
        raise HTTPException(status_code=404, detail="User not found")
    return fetch_all(
        """
        SELECT bots.id, bots.user_id, bots.name, bots.welcome_message, bots.theme_color,
               bots.created_at,
               COUNT(DISTINCT knowledge_sources.id) AS source_count,
               COUNT(DISTINCT conversations.id) AS conversation_count
        FROM bots
        LEFT JOIN knowledge_sources ON knowledge_sources.bot_id = bots.id
        LEFT JOIN conversations ON conversations.bot_id = bots.id
        WHERE bots.user_id = ?
        GROUP BY bots.id
        ORDER BY bots.created_at DESC
        """,
        (user_id,)
    )


@router.put("/bots/{bot_id}")
def update_bot(bot_id: str, bot: BotUpdate):
    if not fetch_one("SELECT id FROM bots WHERE id = ?", (bot_id,)):
        raise HTTPException(status_code=404, detail="Bot not found")
    execute_db(
        "UPDATE bots SET name = ?, welcome_message = ?, theme_color = ? WHERE id = ?",
        (bot.name.strip(), bot.welcome_message.strip(), bot.theme_color, bot_id)
    )
    return fetch_one("SELECT id, user_id, name, welcome_message, theme_color FROM bots WHERE id = ?", (bot_id,))


@router.post("/bots/{bot_id}/transfer-to-admin")
def transfer_bot_to_admin(bot_id: str, current_user: dict = Depends(require_admin)):
    bot = fetch_one("SELECT id, user_id FROM bots WHERE id = ?", (bot_id,))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    execute_db("UPDATE bots SET user_id = ? WHERE id = ?", (current_user["id"], bot_id))
    return {"status": "transferred", "bot_id": bot_id, "user_id": current_user["id"]}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")

    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        target = connection.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if target["role"] == "admin":
            raise HTTPException(status_code=403, detail="Admin accounts cannot be deleted here")

        bot_ids = [row["id"] for row in connection.execute("SELECT id FROM bots WHERE user_id = ?", (user_id,))]
        for bot_id in bot_ids:
            connection.execute("DELETE FROM conversations WHERE bot_id = ?", (bot_id,))
            connection.execute("DELETE FROM knowledge_sources WHERE bot_id = ?", (bot_id,))
            connection.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    for bot_id in bot_ids:
        try:
            delete_bot_knowledge(bot_id)
        except Exception as error:
            print(f"Could not remove vector data for deleted bot {bot_id}: {error}")

    return {"status": "deleted", "deleted_bots": len(bot_ids)}


@router.post("/users/{user_id}/password")
def reset_user_password(user_id: str, reset: PasswordReset):
    if not fetch_one("SELECT id FROM users WHERE id = ?", (user_id,)):
        raise HTTPException(status_code=404, detail="User not found")
    execute_db(
        "UPDATE users SET password_hash = ?, auth_version = auth_version + 1 WHERE id = ?",
        (pwd_context.hash(reset.password), user_id)
    )
    return {"status": "password_updated"}