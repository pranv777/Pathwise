"""Seed the vector knowledge base with starter career guides, interview
prep material, and learning resources shipped in data/knowledge_base/.

Run with:  python -m app.rag.ingest
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.rag.vector_store import add_document, get_store


def ingest_seed_kb() -> dict:
    kb_dir = Path(settings.knowledge_base_dir)
    seed_file = kb_dir / "seed_documents.json"
    if not seed_file.exists():
        return {"ingested": 0, "message": f"No seed file at {seed_file}"}

    docs = json.loads(seed_file.read_text())
    total_chunks = 0
    for doc in docs:
        total_chunks += add_document(
            text=doc["text"],
            source=doc["source"],
            doc_type=doc["doc_type"],
            stable_ids=True,
        )
    return {"ingested": len(docs), "chunks": total_chunks}


def seed_if_empty() -> dict:
    """Seed only when the store is empty (Render's disk is ephemeral)."""
    existing = get_store()._collection.count()
    if existing:
        return {"skipped": True, "existing_chunks": existing}
    return ingest_seed_kb()


if __name__ == "__main__":
    result = ingest_seed_kb()
    print(f"Seeded knowledge base: {result}")
