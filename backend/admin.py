from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import pwd_context, require_admin
from database import execute_db, fetch_all, fetch_one

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


class BotUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    welcome_message: str = Field(min_length=1, max_length=2000)
    theme_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


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


@router.post("/users/{user_id}/password")
def reset_user_password(user_id: str, reset: PasswordReset):
    if not fetch_one("SELECT id FROM users WHERE id = ?", (user_id,)):
        raise HTTPException(status_code=404, detail="User not found")
    execute_db(
        "UPDATE users SET password_hash = ?, auth_version = auth_version + 1 WHERE id = ?",
        (pwd_context.hash(reset.password), user_id)
    )
    return {"status": "password_updated"}