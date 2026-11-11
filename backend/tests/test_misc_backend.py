import asyncio
import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from app import main
from app.auth import mailer
from app.config import Settings, settings
from app.rag import ingest


def _resend(status=200, text=""):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    if status >= 400:
        resp.raise_for_status.side_effect = RuntimeError(f"HTTP {status}")
    return resp


def test_mailer_logs_the_code_in_development(monkeypatch, caplog):
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "environment", "development")
    with caplog.at_level(logging.WARNING, logger="app.auth.mailer"):
        mailer.send_otp_email("a@b.c", "Asha", "123456")
    assert "123456" in caplog.text


def test_mailer_refuses_to_run_unconfigured_in_production(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        mailer.send_otp_email("a@b.c", "Asha", "123456")


def test_mailer_posts_to_resend(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "key")
    with patch("app.auth.mailer.httpx.post", return_value=_resend()) as post:
        mailer.send_otp_email("a@b.c", "Asha", "123456")
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer key"
    assert kwargs["json"]["to"] == ["a@b.c"]
    assert "123456" in kwargs["json"]["subject"]
    assert "Asha" in kwargs["json"]["html"]


def test_mailer_logs_and_raises_on_resend_errors(monkeypatch, caplog):
    monkeypatch.setattr(settings, "resend_api_key", "key")
    with (
        patch("app.auth.mailer.httpx.post", return_value=_resend(403, "bad domain")),
        caplog.at_level(logging.ERROR, logger="app.auth.mailer"),
        pytest.raises(RuntimeError),
    ):
        mailer.send_otp_email("a@b.c", "Asha", "123456")
    assert "bad domain" in caplog.text


def test_ingest_without_a_seed_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_base_dir", str(tmp_path))
    out = ingest.ingest_seed_kb()
    assert out["ingested"] == 0 and "No seed file" in out["message"]


def test_ingest_adds_every_seed_document(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "knowledge_base_dir", str(tmp_path))
    docs = [
        {"text": "a", "source": "a.txt", "doc_type": "career_guide"},
        {"text": "b", "source": "b.txt", "doc_type": "interview_prep"},
    ]
    (tmp_path / "seed_documents.json").write_text(json.dumps(docs))
    with patch("app.rag.ingest.add_document", return_value=2) as add:
        out = ingest.ingest_seed_kb()
    assert out == {"ingested": 2, "chunks": 4}
    assert add.call_args.kwargs["stable_ids"] is True


def test_seed_if_empty_skips_a_populated_store():
    store = MagicMock()
    store._collection.count.return_value = 7
    with patch("app.rag.ingest.get_store", return_value=store):
        assert ingest.seed_if_empty() == {"skipped": True, "existing_chunks": 7}


def test_seed_if_empty_seeds_an_empty_store():
    store = MagicMock()
    store._collection.count.return_value = 0
    with (
        patch("app.rag.ingest.get_store", return_value=store),
        patch("app.rag.ingest.ingest_seed_kb", return_value={"ingested": 1}) as seed,
    ):
        assert ingest.seed_if_empty() == {"ingested": 1}
    seed.assert_called_once()


def _run_lifespan():
    async def go():
        async with main.lifespan(main.app):
            pass

    asyncio.run(go())


def test_startup_warns_about_missing_keys(monkeypatch, caplog):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "google_api_key", "")
    with caplog.at_level(logging.WARNING, logger="startup"):
        _run_lifespan()
    assert "GROQ_API_KEY" in caplog.text and "GOOGLE_API_KEY" in caplog.text


def test_startup_seeds_when_enabled(monkeypatch, caplog):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "google_api_key", "k")
    monkeypatch.setattr(settings, "seed_on_startup", True)
    seed = MagicMock(return_value={"skipped": True})
    monkeypatch.setattr(main, "seed_if_empty", seed)
    with caplog.at_level(logging.INFO, logger="startup"):
        _run_lifespan()
    seed.assert_called_once()
    assert "KB seed" in caplog.text


def test_startup_survives_a_seeding_failure(monkeypatch, caplog):
    monkeypatch.setattr(settings, "google_api_key", "k")
    monkeypatch.setattr(settings, "seed_on_startup", True)
    monkeypatch.setattr(main, "seed_if_empty", MagicMock(side_effect=RuntimeError))
    with caplog.at_level(logging.ERROR, logger="startup"):
        _run_lifespan()
    assert "seeding failed" in caplog.text


def test_startup_does_not_seed_by_default(monkeypatch):
    monkeypatch.setattr(settings, "google_api_key", "k")
    monkeypatch.setattr(settings, "seed_on_startup", False)
    seed = MagicMock()
    monkeypatch.setattr(main, "seed_if_empty", seed)
    _run_lifespan()
    seed.assert_not_called()


def test_root_and_health_endpoints(client):
    assert client.get("/").json()["status"] == "ok"
    health = client.get("/api/health").json()
    assert health["status"] == "healthy"
    assert set(health) >= {"gemini_configured", "tavily_configured", "llm_provider"}


PROD = {
    "environment": "production",
    "google_api_key": "g",
    "groq_api_key": "q",
    "resend_api_key": "r",
    "jwt_secret_key": "x" * 40,
    "database_url": "postgresql://u:p@h/db",
    "cookie_secure": True,
    "cors_origins": "https://app.example.com",
}


def _settings(**overrides):
    return Settings(**{**PROD, **overrides})


def test_a_complete_production_config_is_accepted():
    assert _settings().database_url == "postgresql+psycopg://u:p@h/db"


@pytest.mark.parametrize(
    "override, message",
    [
        ({"google_api_key": ""}, "GOOGLE_API_KEY"),
        ({"groq_api_key": ""}, "GROQ_API_KEY"),
        ({"resend_api_key": ""}, "RESEND_API_KEY"),
        ({"jwt_secret_key": "short"}, "JWT_SECRET_KEY"),
        ({"jwt_secret_key": "change-me-in-.env"}, "JWT_SECRET_KEY"),
        ({"database_url": "sqlite:///x.db"}, "PostgreSQL"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"cors_origins": "http://localhost:5173"}, "CORS_ORIGINS"),
    ],
)
def test_production_config_problems_are_reported(override, message):
    with pytest.raises(ValueError, match=message):
        _settings(**override)


def test_groq_key_is_not_required_for_gemini_in_production():
    assert _settings(llm_provider="gemini", groq_api_key="").llm_provider == "gemini"


def test_development_config_is_lenient():
    assert Settings(environment="development").environment == "development"


def test_database_url_prefixes_are_normalised():
    assert Settings(database_url="postgres://u@h/d").database_url == "postgresql+psycopg://u@h/d"
    assert Settings(database_url="sqlite:///a.db").database_url == "sqlite:///a.db"


def test_derived_settings():
    s = Settings(
        cors_origins=" http://a.test , ,http://b.test",
        llm_provider="gemini",
        gemini_model="g-model",
    )
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]
    assert s.llm_model_name == "g-model"
    assert Settings(llm_provider="groq").llm_model_name == s.groq_model
