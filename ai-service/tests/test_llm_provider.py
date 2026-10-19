from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import agent, main, writer
from app.config import Settings, settings
from app.writer import LLMProviderError


def r103_evidence():
    return [
        {
            "report_id": "R-103",
            "report_title": "Residential Water Purifier Market 2025",
            "page": 5,
            "score": 0.61,
            "text": "Included products are countertop, under-sink, and whole-home residential purification systems and their original-equipment replacement filters. Commercial and municipal treatment systems are excluded.",
        },
        {
            "report_id": "R-103",
            "report_title": "Residential Water Purifier Market 2025",
            "page": 4,
            "score": 0.75,
            "text": "The report discusses replacement demand, distribution, and service revenue. No global numeric market-size figure is provided in this synthetic corpus.",
        },
    ]


def test_settings_accept_groq_and_reject_unknown_provider():
    assert Settings(llm_provider="GROQ").llm_provider == "groq"
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        Settings(llm_provider="unknown")


def test_groq_missing_key_fails_before_constructing_client(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(writer, "ChatOpenAI", lambda **_kwargs: pytest.fail("client must not be constructed"))
    with pytest.raises(LLMProviderError) as caught:
        writer.write_answer("What products are included?", r103_evidence())
    assert caught.value.category == "missing_api_key"
    assert "GROQ_API_KEY" in caught.value.public_message


def test_groq_generation_passes_report_text_and_metadata_to_model(monkeypatch):
    captured = {}
    answer_text = "It includes countertop, under-sink, and whole-home residential systems and their replacement filters; commercial and municipal systems are excluded."

    class FakeChatModel:
        def __init__(self, **kwargs):
            captured["model_kwargs"] = kwargs

        def invoke(self, messages):
            captured["messages"] = messages
            return SimpleNamespace(
                content=answer_text,
                usage_metadata={"input_tokens": 120, "output_tokens": 27},
                response_metadata={},
            )

    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-secret-never-logged")
    monkeypatch.setattr(settings, "model_name", "openai/gpt-oss-120b")
    monkeypatch.setattr(writer, "ChatOpenAI", FakeChatModel)
    result = writer.write_answer("For report R-103, what products are included?", r103_evidence())

    assert result["answer"] == answer_text
    assert result["input_tokens"] == 120
    assert captured["model_kwargs"]["api_key"] == "test-secret-never-logged"
    assert captured["model_kwargs"]["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["model_kwargs"]["model"] == "openai/gpt-oss-120b"
    assert captured["model_kwargs"]["max_completion_tokens"] == 700
    assert captured["model_kwargs"]["temperature"] == 0
    human_prompt = captured["messages"][1][1]
    assert "R-103" in human_prompt and "page=5" in human_prompt
    assert "countertop, under-sink, and whole-home" in human_prompt
    assert "No global numeric market-size figure is provided" in human_prompt
    system_prompt = captured["messages"][0][1]
    assert "[[INSUFFICIENT_EVIDENCE]]" in system_prompt
    assert "do not strengthen that to 'focuses on'" in system_prompt


def test_writer_removes_untrusted_inline_line_citations(monkeypatch):
    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass
        def invoke(self, _messages):
            return SimpleNamespace(content="The report includes these systems. 【5†L1-L4】", usage_metadata={})

    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(writer, "ChatOpenAI", FakeChatModel)
    result = writer.write_answer("What products are included?", r103_evidence())
    assert result["answer"] == "The report includes these systems."


def test_malformed_provider_response_has_distinct_safe_error(monkeypatch):
    class FakeChatModel:
        def __init__(self, **_kwargs):
            pass
        def invoke(self, _messages):
            return SimpleNamespace(content=None)
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(writer, "ChatOpenAI", FakeChatModel)
    with pytest.raises(LLMProviderError) as caught:
        writer.write_answer("What products are included?", r103_evidence())
    assert caught.value.category == "malformed_response"
    assert caught.value.status_code == 502


def test_writer_parses_evidence_abstention_marker(monkeypatch):
    class FakeChatModel:
        def __init__(self, **_kwargs): pass
        def invoke(self, _messages):
            return SimpleNamespace(content="[[INSUFFICIENT_EVIDENCE]] The report does not identify a leading brand.", usage_metadata={})
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(writer, "ChatOpenAI", FakeChatModel)
    result = writer.write_answer("Which brand led?", r103_evidence())
    assert result["answer"] == "The report does not identify a leading brand."
    assert result["evidence_sufficient"] is False


def test_agent_escalates_explicit_evidence_abstention(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {
        "answer": "The report does not identify a leading brand.", "evidence_sufficient": False,
    })
    result = agent.answer({"question": "Which brand had the highest market share in R-103?",
                           "allowed": {"R-103"}, "route": "factual_lookup", "evidence": r103_evidence()})
    assert result["confidence"] >= settings.confidence_threshold
    assert result["escalation_reason"] == "Retrieved evidence does not support the requested fact."
    assert result["generation_outcome"] == "insufficient_evidence"


def test_provider_errors_are_classified_without_forwarding_raw_error_text():
    class FakeProviderError(Exception):
        status_code = 404

    error = writer._provider_error(FakeProviderError("secret-bearing provider body"), "groq")
    assert error.status_code == 502
    assert error.category == "model_or_request"
    assert "MODEL_NAME" in error.public_message
    assert "secret-bearing" not in error.public_message

    timeout = writer._provider_error(TimeoutError("private timeout details"), "groq")
    assert timeout.status_code == 504
    assert timeout.category == "timeout"
    assert "private timeout details" not in timeout.public_message

    class RateLimitError(Exception):
        status_code = 429

    limited = writer._provider_error(RateLimitError("provider body"), "groq")
    assert limited.status_code == 429
    assert limited.category == "rate_limit"


@pytest.mark.parametrize(
    ("failure", "status", "category"),
    [
        (TimeoutError("private timeout detail"), 504, "timeout"),
        (type("NotFoundError", (Exception,), {"status_code": 404})("private model response"), 502, "model_or_request"),
        (type("RateLimitError", (Exception,), {"status_code": 429})("private rate-limit response"), 429, "rate_limit"),
    ],
)
def test_write_answer_maps_mocked_provider_failures_safely(monkeypatch, failure, status, category):
    class FailingChatModel:
        def __init__(self, **_kwargs):
            pass
        def invoke(self, _messages):
            raise failure

    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(writer, "ChatOpenAI", FailingChatModel)
    with pytest.raises(LLMProviderError) as caught:
        writer.write_answer("What does the report say?", r103_evidence())
    assert caught.value.status_code == status
    assert caught.value.category == category
    assert "private" not in caught.value.public_message


def test_agent_returns_grounded_answer_with_retrieved_r103_citations(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    answer_text = "It includes countertop, under-sink, and whole-home residential systems and their replacement filters (page 5). Commercial and municipal systems are excluded (page 5)."
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {"status": "verified", "claims": []})
    monkeypatch.setattr(agent, "write_answer", lambda _question, evidence: {
        "answer": answer_text, "input_tokens": 40, "output_tokens": 30, "estimated_cost": None,
    })
    result = agent.answer({
        "question": "For report R-103, what residential products are included?",
        "allowed": {"R-103"}, "route": "factual_lookup", "evidence": r103_evidence(),
    })
    assert result["answer"] == answer_text
    assert {(c["report_id"], c["page"]) for c in result["citations"]} == {("R-103", 4), ("R-103", 5)}
    assert result["confidence"] >= settings.confidence_threshold
    assert "escalation_reason" not in result
    assert result["retrieved_chunk_count"] == 2
    assert result["source_pages"] == [{"report_id": "R-103", "page": 4}, {"report_id": "R-103", "page": 5}]
    assert result["confidence_components"]["score"] == result["confidence"]


def test_repeated_product_question_is_consistent_and_cited(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    answer_text = "Countertop, under-sink, and whole-home residential systems and replacement filters are included (page 5)."
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {"status": "verified", "claims": []})
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": answer_text, "provider": "groq", "model": "test-model"})
    state = {"question": "For report R-103, what residential products are included? Cite the relevant pages.",
             "allowed": {"R-103"}, "route": "factual_lookup", "evidence": r103_evidence()}
    first = agent.answer(state)
    second = agent.answer(state)
    assert first["answer"] == second["answer"]
    assert first["confidence"] == second["confidence"] >= 0.70
    assert first["citations"] == second["citations"]
    assert {c["page"] for c in first["citations"]} == {4, 5}


def test_main_findings_summary_requires_support_from_context(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    summary = "The findings cover residential product scope, replacement demand, distribution, and service revenue (page 4)."
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {"status": "verified", "claims": []})
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": summary})
    result = agent.answer({"question": "What are the main findings of report R-103? Summarize findings supported by retrieved report content.",
                           "allowed": {"R-103"}, "route": "factual_lookup", "evidence": r103_evidence()})
    assert result["answer"] == summary
    assert result["confidence"] >= 0.70
    assert {c["page"] for c in result["citations"]} == {4, 5}


def test_main_findings_with_insufficient_context_escalates(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    weak = [{**r103_evidence()[0], "score": 0.1}]
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": "The report has findings."})
    result = agent.answer({"question": "What are all the main findings of R-103?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": weak})
    assert result["confidence"] < 0.70
    assert result["escalation_reason"]


def test_chat_response_mapping_preserves_answer_citations_confidence(monkeypatch):
    # The browser-rendered portal consumes this same API response shape; ensure
    # the API schema has not replaced or dropped the generated answer.
    from app.schemas import ChatResponse, Citation
    response = ChatResponse(answer="Grounded answer", citations=[Citation(report_id="R-103", report_title="Report", page=5, quote="Evidence")],
                            confidence=0.82, escalated=False, request_id="req")
    payload = response.model_dump()
    assert payload["answer"] == "Grounded answer"
    assert payload["citations"][0]["page"] == 5
    assert payload["citations"][0]["report_id"] == "R-103"
    assert payload["confidence"] == 0.82


def test_low_relevance_still_escalates_and_keeps_citations(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _question, _evidence: {
        "answer": "The report covers residential products.", "input_tokens": 20, "output_tokens": 8,
    })
    weak = [{**r103_evidence()[0], "score": 0.1}]
    result = agent.answer({
        "question": "Explain an unrelated geopolitical event using this report.",
        "allowed": {"R-103"}, "route": "factual_lookup", "evidence": weak,
    })
    assert result["confidence"] < settings.confidence_threshold
    assert result["escalation_reason"]
    assert result["citations"][0]["report_id"] == "R-103"


def test_unsupported_numeric_answer_escalates_with_source_citations(monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    bad_answer = "The market was USD 9.99 billion."
    monkeypatch.setattr(agent, "write_answer", lambda _question, _evidence: {
        "answer": bad_answer, "input_tokens": 20, "output_tokens": 8,
    })
    correction_calls = []
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: (correction_calls.append(True) or {"answer": bad_answer}))
    result = agent.answer({
        "question": "What is the market size in report R-103?",
        "allowed": {"R-103"}, "route": "factual_lookup", "evidence": r103_evidence(),
    })
    assert result["escalation_reason"] == "Numeric claim failed evidence check."
    assert len(correction_calls) == 1
    # Confidence remains retrieval/citation support semantics; numeric guard
    # rejection is represented by escalation and must not rewrite that score.
    assert result["confidence"] == 0.88
    assert all(citation["report_id"] == "R-103" for citation in result["citations"])


def test_api_returns_safe_configuration_error_instead_of_analyst_fallback(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def execute(self, *_args, **_kwargs):
            return SimpleNamespace(scalar=lambda: None)

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(main.settings, "api_key", "test-api-key")
    monkeypatch.setattr(main, "entitled_reports", lambda _client: {"R-103"})
    monkeypatch.setattr(main, "engine", FakeEngine())
    def fail_provider(_state):
        raise LLMProviderError("missing_api_key", 503, "Groq is selected but GROQ_API_KEY is missing.")
    monkeypatch.setattr(main, "workflow", SimpleNamespace(invoke=fail_provider))

    response = TestClient(main.app).post(
        "/chat", headers={"X-API-Key": "test-api-key"},
        json={"client_id": "C-01", "message": "For report R-103, what products are included?"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Groq is selected but GROQ_API_KEY is missing."
    assert "analyst" not in response.text.lower()
