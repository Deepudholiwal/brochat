import chromadb
import os
from pathlib import Path
import hashlib
import shutil
from database import DATA_DIR, DATABASE_URL, execute_db, fetch_all, fetch_one, is_render_runtime

LEGACY_CHROMA_DIR = Path(__file__).parent / "chroma_data"
DEFAULT_CHROMA_DIR = DATA_DIR if is_render_runtime() else LEGACY_CHROMA_DIR
CHROMA_DIR = Path(os.environ.get("CHROMA_PATH", DEFAULT_CHROMA_DIR))
if not DATABASE_URL and CHROMA_DIR != LEGACY_CHROMA_DIR and LEGACY_CHROMA_DIR not in CHROMA_DIR.resolve().parents and not CHROMA_DIR.exists() and LEGACY_CHROMA_DIR.exists():
    shutil.copytree(LEGACY_CHROMA_DIR, CHROMA_DIR)

client = chromadb.PersistentClient(path=str(CHROMA_DIR)) if not DATABASE_URL else None

def get_collection(bot_id: str):
    if DATABASE_URL:
        raise RuntimeError("Chroma collections are unavailable when PostgreSQL knowledge storage is enabled")
    return client.get_or_create_collection(name=f"bot_{bot_id}")

def add_chunks(bot_id: str, source_url: str, chunks: list[str], page_title: str):
    if DATABASE_URL:
        for index, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{source_url}_{index}_{chunk}".encode()).hexdigest()
            execute_db(
                """
                INSERT INTO knowledge_chunks (id, bot_id, source, title, content)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content
                """,
                (chunk_id, bot_id, source_url, page_title, chunk),
            )
        return

    collection = get_collection(bot_id)
    
    ids = []
    metadatas = []
    documents = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{source_url}_{i}_{chunk}".encode()).hexdigest()
        ids.append(chunk_id)
        metadatas.append({"source": source_url, "title": page_title})
        documents.append(chunk)
        
    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

def query_chunks(bot_id: str, question: str, top_k: int = 5):
    if DATABASE_URL:
        return fetch_all(
            """
            SELECT content AS text, source, title
            FROM knowledge_chunks
            WHERE bot_id = ?
              AND to_tsvector('simple', content) @@ plainto_tsquery('simple', ?)
            ORDER BY ts_rank_cd(to_tsvector('simple', content), plainto_tsquery('simple', ?)) DESC
            LIMIT ?
            """,
            (bot_id, question, question, top_k),
        )

    try:
        collection = get_collection(bot_id)
        results = collection.query(
            query_texts=[question],
            n_results=top_k
        )
        
        matches = []
        if results['documents'] and len(results['documents']) > 0:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            for doc, meta in zip(docs, metas):
                matches.append({
                    "text": doc,
                    "source": meta.get("source", ""),
                    "title": meta.get("title", "")
                })
        return matches
    except Exception as e:
        print(f"Vector store query error: {e}")
        return []

def delete_source_chunks(bot_id: str, source_url: str):
    if DATABASE_URL:
        execute_db("DELETE FROM knowledge_chunks WHERE bot_id = ? AND source = ?", (bot_id, source_url))
        return
    collection = get_collection(bot_id)
    collection.delete(where={"source": source_url})


def delete_bot_knowledge(bot_id: str):
    if DATABASE_URL:
        execute_db("DELETE FROM knowledge_chunks WHERE bot_id = ?", (bot_id,))
        return
    collection_name = f"bot_{bot_id}"
    if collection_name in {item.name for item in client.list_collections()}:
        client.delete_collection(collection_name)


def restore_vector_documents(bot_id: str, ids: list[str], documents: list[str], metadatas: list[dict], embeddings=None) -> int:
    if not ids or not (len(ids) == len(documents) == len(metadatas)):
        return 0
    if DATABASE_URL:
        restored = 0
        for item_id, document, metadata in zip(ids, documents, metadatas):
            existing = fetch_one("SELECT id FROM knowledge_chunks WHERE id = ?", (item_id,))
            if existing:
                continue
            execute_db(
                "INSERT INTO knowledge_chunks (id, bot_id, source, title, content) VALUES (?, ?, ?, ?, ?)",
                (item_id, bot_id, metadata.get("source", ""), metadata.get("title", ""), document),
            )
            restored += 1
        return restored

    collection = get_collection(bot_id)
    existing_ids = set(collection.get(ids=ids, include=[])['ids'])
    missing_indexes = [index for index, item_id in enumerate(ids) if item_id not in existing_ids]
    if not missing_indexes:
        return 0
    values = {
        "ids": [ids[index] for index in missing_indexes],
        "documents": [documents[index] for index in missing_indexes],
        "metadatas": [metadatas[index] for index in missing_indexes],
    }
    if embeddings is not None and len(embeddings) == len(ids):
        values["embeddings"] = [embeddings[index] for index in missing_indexes]
    collection.add(**values)
    return len(missing_indexes)
