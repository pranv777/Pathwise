import sys
from types import ModuleType, SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from langchain_core.exceptions import OutputParserException

from app.config import settings
from app.models.llm_outputs import JobMatchOut
from app.utils import llm, structured

GOOD = {"match_score": 70, "matched_skills": [], "missing_skills": [], "rationale": "ok"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(llm, "_llms", {})
    monkeypatch.setattr(settings, "llm_output_mode", "structured")
    monkeypatch.setattr("time.sleep", lambda *_: None)
    structured.stats.clear()
    yield
    structured.stats.clear()


def _fake_module(monkeypatch, name, cls_name):
    created = []

    class Fake:
        def __init__(self, **kwargs):
            created.append(kwargs)

    module = ModuleType(name)
    setattr(module, cls_name, Fake)
    monkeypatch.setitem(sys.modules, name, module)
    return Fake, created


def test_groq_requires_a_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm._build_llm(0.1)


def test_gemini_requires_a_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "google_api_key", "")
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        llm._build_llm(0.1)


def test_groq_model_is_built_with_the_configured_options(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "k")
    fake, created = _fake_module(monkeypatch, "langchain_groq", "ChatGroq")
    assert isinstance(llm._build_llm(0.4), fake)
    assert created[0]["temperature"] == 0.4
    assert created[0]["api_key"].get_secret_value() == "k"
    assert created[0]["model"] == settings.groq_model


def test_gemini_model_is_built_with_the_configured_options(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "google_api_key", "k")
    fake, created = _fake_module(monkeypatch, "langchain_google_genai", "ChatGoogleGenerativeAI")
    assert isinstance(llm._build_llm(0.2), fake)
    assert created[0]["model"] == settings.gemini_model


def test_get_llm_builds_once_per_temperature(monkeypatch):
    build = MagicMock(side_effect=lambda t: object())
    monkeypatch.setattr(llm, "_build_llm", build)
    first = llm.get_llm(0.1)
    assert llm.get_llm(0.1) is first
    assert llm.get_llm(0.9) is not first
    assert build.call_count == 2


def test_response_text_joins_content_blocks():
    msg = SimpleNamespace(content=["a", {"type": "text", "text": "b"}, {"type": "image"}, 5])
    assert llm.response_text(cast(Any, msg)) == "ab"
    assert llm.response_text(cast(Any, SimpleNamespace(content="plain"))) == "plain"


@pytest.mark.parametrize("text", ["{}", "[1, 2]", "no json here"])
def test_extract_json_rejects_empty_or_non_object_output(text):
    with pytest.raises(ValueError):
        llm.extract_json(text)


def _runnable(result):
    model = MagicMock()
    model.with_structured_output.return_value.invoke.return_value = result
    return model


def test_structured_call_accepts_instances_and_dicts(monkeypatch):
    instance = JobMatchOut(**GOOD)
    monkeypatch.setattr(structured, "get_llm", lambda t: _runnable(instance))
    assert structured._call_structured(JobMatchOut, [], 0.2) is instance
    monkeypatch.setattr(structured, "get_llm", lambda t: _runnable(GOOD))
    assert structured._call_structured(JobMatchOut, [], 0.2) == instance


def test_structured_call_rejects_a_missing_result(monkeypatch):
    monkeypatch.setattr(structured, "get_llm", lambda t: _runnable(None))
    with pytest.raises(structured.StructuredOutputError):
        structured._call_structured(JobMatchOut, [], 0.2)


def test_legacy_call_parses_json_text(monkeypatch):
    model = MagicMock()
    model.invoke.return_value = SimpleNamespace(
        content='```json\n{"match_score": 5, "matched_skills": [], "missing_skills": [], "rationale": "r"}\n```'
    )
    monkeypatch.setattr(structured, "get_llm", lambda t: model)
    assert structured._call_legacy(JobMatchOut, [], 0.2).match_score == 5


def test_legacy_call_turns_parse_failures_into_structured_errors(monkeypatch):
    model = MagicMock()
    model.invoke.return_value = SimpleNamespace(content="nothing useful")
    monkeypatch.setattr(structured, "get_llm", lambda t: model)
    with pytest.raises(structured.StructuredOutputError):
        structured._call_legacy(JobMatchOut, [], 0.2)


def test_retries_are_exhausted_and_counted(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_attempts", 3)
    call = MagicMock(side_effect=OutputParserException("bad"))
    monkeypatch.setattr(structured, "_call_structured", call)
    with pytest.raises(OutputParserException):
        structured.invoke_json(JobMatchOut, [])
    assert call.call_count == 3
    assert structured.stats["retries"] == 2
    assert structured.stats["first_attempt_failures"] == 1
    assert structured.stats["final_failures"] == 1


def test_non_retryable_errors_propagate_immediately(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_attempts", 3)
    call = MagicMock(side_effect=ConnectionError("down"))
    monkeypatch.setattr(structured, "_call_structured", call)
    with pytest.raises(ConnectionError):
        structured.invoke_json(JobMatchOut, [])
    assert call.call_count == 1


def test_legacy_mode_success_uses_a_single_attempt(monkeypatch):
    monkeypatch.setattr(settings, "llm_output_mode", "legacy")
    good = JobMatchOut(**GOOD)
    monkeypatch.setattr(structured, "_call_legacy", MagicMock(return_value=good))
    assert structured.invoke_json(JobMatchOut, []) is good
    assert structured.stats["calls"] == 1
