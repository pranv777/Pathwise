from unittest.mock import MagicMock, patch

from app.rag import vector_store


@patch("app.rag.vector_store.get_store")
def test_add_document_chunks_and_indexes(mock_get_store):
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    n = vector_store.add_document(
        "some resume text " * 50, source="resume.pdf", doc_type="resume", user_id=1
    )
    assert n > 0
    mock_store.add_documents.assert_called_once()


@patch("app.rag.vector_store.get_store")
def test_search_failure_returns_empty_list(mock_get_store):
    mock_get_store.side_effect = Exception("chroma down")
    results = vector_store.search("query")
    assert results == []


@patch("app.rag.vector_store.get_store")
def test_search_uses_and_filter_for_multi_key(mock_get_store):
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    vector_store.search("query", doc_type="resume", user_id=1)
    _, kwargs = mock_store.similarity_search_with_relevance_scores.call_args
    assert kwargs["filter"] == {"$and": [{"doc_type": "resume"}, {"user_id": 1}]}
