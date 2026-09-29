import sqlite3
import os
from pathlib import Path
from datetime import datetime

def is_render_runtime() -> bool:
    return os.environ.get("RENDER", "").lower() == "true" or bool(os.environ.get("RENDER_SERVICE_ID"))


DEFAULT_DATA_DIR = Path(__file__).parent / "chroma_data"
RENDER_DATA_DIR = Path("/var/data")
DATA_DIR = Path(os.environ.get(
    "BROCHAT_DATA_DIR",
    RENDER_DATA_DIR if is_render_runtime() else DEFAULT_DATA_DIR,
))
DEFAULT_DB_PATH = DATA_DIR / "brochat.db" if is_render_runtime() else Path(__file__).parent / "brochat.db"
DB_PATH = Path(os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
LEGACY_DB_PATH = Path(__file__).parent / "brochat.db"
MOUNT_INFO_PATH = Path("/proc/self/mountinfo")


def validate_persistent_storage() -> bool:
    configured_root = os.environ.get("BROCHAT_DATA_DIR")
    if not configured_root and is_render_runtime():
        configured_root = str(RENDER_DATA_DIR)
    if not configured_root:
        return False

    root = Path(configured_root).resolve()
    if not MOUNT_INFO_PATH.exists():
        raise RuntimeError("Cannot verify the configured persistent data disk mount")

    mounted_paths = set()
    for line in MOUNT_INFO_PATH.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) > 4:
            mount_path = fields[4].replace("\\040", " ").replace("\\011", "\t")
            mounted_paths.add(Path(mount_path).resolve())

    if root not in mounted_paths:
        raise RuntimeError(
            f"Persistent disk is not mounted at {root}. Attach the brochat-data disk at this exact path before deploying."
        )

    configured_paths = {
        "DATABASE_PATH": Path(os.environ.get("DATABASE_PATH", root / "brochat.db")),
        "CHROMA_PATH": Path(os.environ.get("CHROMA_PATH", root / "chroma")),
    }
    for name, configured_path in configured_paths.items():
        try:
            configured_path.resolve().relative_to(root)
        except ValueError as error:
            raise RuntimeError(f"{name} must be located inside the persistent disk at {root}") from error

    print(f"Persistent data disk verified at {root}")
    return True


if is_render_runtime():
    validate_persistent_storage()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    validate_persistent_storage()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH != LEGACY_DB_PATH and not DB_PATH.exists() and LEGACY_DB_PATH.exists():
        legacy_conn = sqlite3.connect(LEGACY_DB_PATH)
        persistent_conn = sqlite3.connect(DB_PATH)
        try:
            legacy_conn.backup(persistent_conn)
        finally:
            persistent_conn.close()
            legacy_conn.close()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            auth_version INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')

    user_columns = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
    if "role" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "auth_version" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            welcome_message TEXT,
            theme_color TEXT DEFAULT '#c6ff6d',
            created_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_sources (
            id TEXT PRIMARY KEY,
            bot_id TEXT,
            url TEXT,
            status TEXT DEFAULT 'pending',
            pages_scraped INTEGER DEFAULT 0,
            scrape_started_at TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(bot_id) REFERENCES bots(id)
        )
    ''')

    source_columns = {row[1] for row in cursor.execute("PRAGMA table_info(knowledge_sources)")}
    if "scrape_started_at" not in source_columns:
        cursor.execute("ALTER TABLE knowledge_sources ADD COLUMN scrape_started_at TEXT")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            bot_id TEXT,
            visitor_id TEXT,
            messages TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(bot_id) REFERENCES bots(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def fetch_one(query: str, params: tuple = ()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    res = cur.fetchone()
    conn.close()
    return dict(res) if res else None

def fetch_all(query: str, params: tuple = ()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    res = cur.fetchall()
    conn.close()
    return [dict(r) for r in res]

def execute_db(query: str, params: tuple = ()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    lastrowid = cur.lastrowid
    conn.close()
    return lastrowid
