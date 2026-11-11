from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.rag import vector_store


@pytest.fixture(autouse=True)
def _no_cached_store(monkeypatch):
    monkeypatch.setattr(vector_store, "_store", None)


def test_embeddings_need_a_google_key(monkeypatch):
    monkeypatch.setattr(settings, "google_api_key", "")
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        vector_store.get_embeddings()


def test_embeddings_use_the_configured_model(monkeypatch):
    monkeypatch.setattr(settings, "google_api_key", "k")
    with patch("app.rag.vector_store.GoogleGenerativeAIEmbeddings") as cls:
        vector_store.get_embeddings()
    assert cls.call_args.kwargs["model"] == settings.gemini_embedding_model


def test_store_is_built_once_and_reused():
    with (
        patch("app.rag.vector_store.get_embeddings", return_value="emb"),
        patch("app.rag.vector_store.Chroma") as chroma,
    ):
        first = vector_store.get_store()
        assert vector_store.get_store() is first
    chroma.assert_called_once()
    assert chroma.call_args.kwargs["embedding_function"] == "emb"
    assert chroma.call_args.kwargs["collection_name"] == vector_store.COLLECTION_NAME


def test_empty_text_adds_nothing():
    with patch("app.rag.vector_store.get_store") as get_store:
        assert vector_store.add_document("", "a.txt", "career_guide") == 0
    get_store.assert_not_called()


def test_stable_ids_make_indexing_idempotent_and_user_id_is_stored():
    store = MagicMock()
    with patch("app.rag.vector_store.get_store", return_value=store):
        vector_store.add_document("hello", "a.txt", "resume", user_id=4, stable_ids=True)
        vector_store.add_document("hello", "a.txt", "resume", user_id=4, stable_ids=True)
        vector_store.add_document("hello", "a.txt", "resume", user_id=4)
    first, second, random = store.add_documents.call_args_list
    assert first.kwargs["ids"] == second.kwargs["ids"] != random.kwargs["ids"]
    assert first.args[0][0].metadata == {"source": "a.txt", "doc_type": "resume", "user_id": 4}


def test_delete_user_documents_is_scoped_to_user_and_type():
    store = MagicMock()
    with patch("app.rag.vector_store.get_store", return_value=store):
        vector_store.delete_user_documents(7, "resume")
    store._collection.delete.assert_called_once_with(
        where={"$and": [{"user_id": 7}, {"doc_type": "resume"}]}
    )


@pytest.mark.parametrize("doc_type", sorted(vector_store.USER_SCOPED_TYPES))
def test_private_documents_are_never_searched_without_a_user(doc_type):
    with patch("app.rag.vector_store.get_store") as get_store:
        assert vector_store.search("q", doc_type=doc_type) == []
    get_store.assert_not_called()


def test_unfiltered_search_excludes_private_documents():
    store = MagicMock()
    with patch("app.rag.vector_store.get_store", return_value=store):
        vector_store.search("q")
    assert store.similarity_search_with_relevance_scores.call_args.kwargs["filter"] == {
        "doc_type": {"$nin": ["resume", "user_note"]}
    }


def test_single_condition_search_is_not_wrapped_in_and():
    store = MagicMock()
    with patch("app.rag.vector_store.get_store", return_value=store):
        vector_store.search("q", doc_type="career_guide")
        vector_store.search("q", user_id=3)
    filters = [c.kwargs["filter"] for c in store.similarity_search_with_relevance_scores.call_args_list]
    assert filters == [{"doc_type": "career_guide"}, {"user_id": 3}]
