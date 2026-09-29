import chromadb
import os
from pathlib import Path
import hashlib
import shutil
from database import DATA_DIR, is_render_runtime

LEGACY_CHROMA_DIR = Path(__file__).parent / "chroma_data"
DEFAULT_CHROMA_DIR = DATA_DIR if is_render_runtime() else LEGACY_CHROMA_DIR
CHROMA_DIR = Path(os.environ.get("CHROMA_PATH", DEFAULT_CHROMA_DIR))
if (
    CHROMA_DIR != LEGACY_CHROMA_DIR
    and LEGACY_CHROMA_DIR not in CHROMA_DIR.resolve().parents
    and not CHROMA_DIR.exists()
    and LEGACY_CHROMA_DIR.exists()
):
    shutil.copytree(LEGACY_CHROMA_DIR, CHROMA_DIR)

client = chromadb.PersistentClient(path=str(CHROMA_DIR))

def get_collection(bot_id: str):
    return client.get_or_create_collection(name=f"bot_{bot_id}")

def add_chunks(bot_id: str, source_url: str, chunks: list[str], page_title: str):
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
    collection = get_collection(bot_id)
    collection.delete(where={"source": source_url})
