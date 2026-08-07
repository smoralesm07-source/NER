from types import SimpleNamespace

from openai import OpenAIError

from ner_prensa.llm_engine import adjudicate_with_llm
from ner_prensa.models import Entity


def candidate():
    return Entity(
        mention="Empresa ABC SpA",
        canonical_name="Empresa ABC SpA",
        type="PERSONA_JURIDICA",
        subtype="Empresa",
        evidence="Empresa ABC SpA informó...",
        signals=["gliner2"],
    )


def test_llm_quota_error_falls_back(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponses:
        def create(self, **kwargs):
            raise OpenAIError("429 insufficient_quota credit_balance_exhausted: You have no credits remaining")

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("ner_prensa.llm_engine.OpenAI", lambda: FakeClient())
    c = candidate()
    entities, relations, meta = adjudicate_with_llm("Empresa ABC SpA informó...", [c])

    assert entities == [c]
    assert relations == []
    assert meta["llm_used"] is False
    assert meta["llm_fallback"] is True
    assert "créditos" in str(meta["llm_error"]).lower()


def test_llm_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(output_text='{"entities": [], "relations": []}')

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr("ner_prensa.llm_engine.OpenAI", lambda: FakeClient())
    entities, relations, meta = adjudicate_with_llm("Texto", [])

    assert entities == []
    assert relations == []
    assert meta["llm_used"] is True
    assert meta["llm_fallback"] is False
    assert meta["llm_error"] == ""
