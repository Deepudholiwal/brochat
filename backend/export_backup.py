import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import chromadb


BACKEND_DIR = Path(__file__).parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", BACKEND_DIR / "brochat.db"))
CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", BACKEND_DIR / "chroma_data"))


def export_backup() -> Path:
    connection = sqlite3.connect(f"{DB_PATH.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        data = {
            table: [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]
            if table in tables else []
            for table in ("users", "bots", "knowledge_sources", "conversations")
        }
    finally:
        connection.close()

    chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    vector_collections = []
    for collection in chroma.list_collections():
        if not collection.name.startswith("bot_"):
            continue
        records = collection.get(include=["documents", "metadatas", "embeddings"])
        embeddings = records.get("embeddings")
        vector_collections.append({
            "bot_id": collection.name.removeprefix("bot_"),
            "ids": records.get("ids", []),
            "documents": records.get("documents", []),
            "metadatas": records.get("metadatas", []),
            "embeddings": embeddings.tolist() if embeddings is not None else None,
        })

    backup = {
        "format": "brochat-backup",
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        **data,
        "vector_collections": vector_collections,
    }
    output_path = Path(tempfile.gettempdir()) / f"brochat-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output_path.write_text(json.dumps(backup, ensure_ascii=False), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(export_backup())