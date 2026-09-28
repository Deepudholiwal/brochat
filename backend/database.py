import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "brochat.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TIMESTAMP
        )
    ''')
    
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
            created_at TIMESTAMP,
            FOREIGN KEY(bot_id) REFERENCES bots(id)
        )
    ''')
    
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
