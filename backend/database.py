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
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
LEGACY_DB_PATH = Path(__file__).parent / "brochat.db"
MOUNT_INFO_PATH = Path("/proc/self/mountinfo")


def _prepare_query(query: str) -> str:
    if not DATABASE_URL:
        return query
    query = query.replace("BEGIN IMMEDIATE", "BEGIN")
    if query.lstrip().upper().startswith("INSERT OR IGNORE INTO"):
        query = query.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1).rstrip().rstrip(";")
        query += " ON CONFLICT DO NOTHING"
    return query.replace("?", "%s")


class DatabaseConnection:
    def __init__(self, timeout: int = 10):
        if DATABASE_URL:
            import psycopg
            from psycopg.rows import dict_row

            self.connection = psycopg.connect(DATABASE_URL, connect_timeout=timeout, row_factory=dict_row)
        else:
            self.connection = sqlite3.connect(DB_PATH, timeout=timeout)
            self.connection.row_factory = sqlite3.Row

    def execute(self, query: str, params: tuple = ()):
        return self.connection.execute(_prepare_query(query), params)

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()

    def close(self):
        return self.connection.close()


def connect_database(timeout: int = 10) -> DatabaseConnection:
    return DatabaseConnection(timeout=timeout)


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
    if DATABASE_URL:
        print("External PostgreSQL storage configured")
    elif os.environ.get("BROCHAT_DATA_DIR"):
        validate_persistent_storage()
    else:
        raise RuntimeError(
            "Free Render services have ephemeral filesystems. Configure DATABASE_URL for persistent storage."
        )


def get_db():
    conn = connect_database()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    if not DATABASE_URL:
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

    conn = connect_database()
    
    conn.execute('''
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

    if DATABASE_URL:
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_version INTEGER NOT NULL DEFAULT 0")
    else:
        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "role" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        if "auth_version" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0")
    
    conn.execute('''
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
    
    conn.execute('''
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

    if DATABASE_URL:
        conn.execute("ALTER TABLE knowledge_sources ADD COLUMN IF NOT EXISTS scrape_started_at TEXT")
    else:
        source_columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_sources)")}
        if "scrape_started_at" not in source_columns:
            conn.execute("ALTER TABLE knowledge_sources ADD COLUMN scrape_started_at TEXT")
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            bot_id TEXT,
            visitor_id TEXT,
            messages TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY(bot_id) REFERENCES bots(id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    if DATABASE_URL:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id TEXT PRIMARY KEY,
                bot_id TEXT NOT NULL,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS knowledge_chunks_bot_id_idx ON knowledge_chunks (bot_id)')
    
    conn.commit()
    conn.close()

def fetch_one(query: str, params: tuple = ()):
    conn = connect_database()
    try:
        res = conn.execute(query, params).fetchone()
        return dict(res) if res else None
    finally:
        conn.close()

def fetch_all(query: str, params: tuple = ()):
    conn = connect_database()
    try:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    finally:
        conn.close()

def execute_db(query: str, params: tuple = ()):
    conn = connect_database()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return getattr(cursor, "lastrowid", None)
    finally:
        conn.close()
