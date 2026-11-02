"""Chroma-backed vector store for the Placement Assistant knowledge base.

Holds five kinds of documents (see doc_type): resume, job_description,
interview_prep, learning_resource, career_guide. All agents retrieve
through `search()` before generating recommendations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr

from app.config import settings

logger = logging.getLogger("rag")

_store: Chroma | None = None
COLLECTION_NAME = "placement_assistant_kb"
USER_SCOPED_TYPES = {"resume", "user_note"}


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to backend/.env (see .env.example)."
        )
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=SecretStr(settings.google_api_key),
    )


def get_store() -> Chroma:
    global _store
    if _store is None:
        _store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
        )
    return _store


def add_document(
    text: str,
    source: str,
    doc_type: str,
    user_id: int | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
    stable_ids: bool = False,
) -> int:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_text(text)
    if not chunks:
        return 0

    metadata: dict[str, str | int] = {"source": source, "doc_type": doc_type}
    if user_id is not None:
        metadata["user_id"] = user_id

    docs = [Document(page_content=chunk, metadata=metadata) for chunk in chunks]
    # stable_ids makes seeding idempotent (re-running upserts instead of duplicating)
    ids = [
        str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}:{doc_type}:{i}"))
        if stable_ids
        else str(uuid.uuid4())
        for i in range(len(docs))
    ]
    get_store().add_documents(docs, ids=ids)
    return len(docs)


def delete_user_documents(user_id: int, doc_type: str) -> None:
    """Remove a user's previous docs of a type (e.g. old resume on re-upload)."""
    get_store()._collection.delete(
        where={"$and": [{"user_id": user_id}, {"doc_type": doc_type}]}
    )


def search(
    query: str, k: int = 4, doc_type: str | None = None, user_id: int | None = None
):
    if doc_type is not None and doc_type in USER_SCOPED_TYPES and user_id is None:
        logger.warning("Refusing unscoped search over private doc_type=%s", doc_type)
        return []
    try:
        store = get_store()
        conditions: list[dict[str, Any]] = []
        if doc_type:
            conditions.append({"doc_type": doc_type})
        if user_id is not None:
            conditions.append({"user_id": user_id})
        if doc_type is None and user_id is None:
            # shared knowledge base only: never surface anyone's private docs
            conditions.append({"doc_type": {"$nin": sorted(USER_SCOPED_TYPES)}})

        filter_: dict[str, Any] = (
            conditions[0] if len(conditions) == 1 else {"$and": conditions}
        )
        return store.similarity_search_with_relevance_scores(query, k=k, filter=filter_)
    except Exception as exc:  # noqa: BLE001 - RAG is best-effort; never break the caller
        logger.warning(f"RAG search failed (query={query!r}): {exc}")
        return []
