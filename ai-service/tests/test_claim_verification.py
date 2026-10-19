import json
from types import SimpleNamespace

from app import agent, critic, writer


def evidence(text="The report discusses replacement demand.", page=4):
    return [{"report_id": "R-103", "report_title": "Residential Water Purifier Market 2025",
             "page": page, "score": 0.75, "text": text}]


class VerdictModel:
    def __init__(self, supported=True):
        self.supported = supported
        self.prompt = None

    def invoke(self, messages):
        self.prompt = messages[1][1]
        payload = json.loads(self.prompt)
        return SimpleNamespace(content=json.dumps({"claims": [
            {"claim": item["claim"], "supported": self.supported[index] if isinstance(self.supported, list) else self.supported}
            for index, item in enumerate(payload["claims"])
        ]}))


def mock_critic(monkeypatch, model):
    monkeypatch.setattr(critic, "_make_model", lambda _provider: model)


def test_fully_supported_claim_is_verified(monkeypatch):
    model = VerdictModel()
    mock_critic(monkeypatch, model)
    result = critic.verify_claims("The report discusses replacement demand (page 4).", evidence())
    assert result["status"] == "verified", result
    assert result["claims"] == [{"claim": "The report discusses replacement demand", "pages": [4], "status": "supported"}]
    assert "The report discusses replacement demand." in model.prompt


def test_page_abbreviation_and_report_qualified_citations_are_parsed(monkeypatch):
    model = VerdictModel()
    mock_critic(monkeypatch, model)
    passages = evidence("Replacement filters are included.", 5) + [{
        "report_id": "R-101", "report_title": "Other report", "page": 4, "score": 0.7,
        "text": "The global market is defined in this passage.",
    }]
    answer = "R-101, p. 4: The global market is defined here. R-103, page 5: replacement filters are included."
    result = critic.verify_claims(answer, passages)
    assert result["status"] == "verified", result
    assert [claim["pages"] for claim in result["claims"]] == [[4], [5]]


def test_emphasis_upgrade_from_discusses_to_focuses_is_rejected_deterministically():
    result = critic.verify_claims("The report focuses on replacement demand (page 4).", evidence())
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported_wording"


def test_unsupported_causal_claim_is_rejected_deterministically():
    result = critic.verify_claims("Replacement demand is driven by distribution (page 4).", evidence())
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported_wording"


def test_mixed_supported_and_unsupported_assertions_are_verified_separately(monkeypatch):
    model = VerdictModel(supported=[True, False])
    mock_critic(monkeypatch, model)
    answer = "The report discusses replacement demand and it reports a market share percentage (page 4)."
    result = critic.verify_claims(answer, evidence())
    assert result["status"] == "rejected"
    assert [item["status"] for item in result["claims"]] == ["supported", "unsupported"]


def test_unparsed_coordinated_predicates_fail_closed():
    result = critic.verify_claims("The report discusses replacement demand and highlights channel trends (page 4).", evidence())
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "compound_claim_requires_review"


def test_r103_page8_qualitative_and_nonquantification_claim_is_reviewed_separately(monkeypatch):
    model = VerdictModel()
    mock_critic(monkeypatch, model)
    page8 = evidence(
        "The report provides qualitative regional outlook and does not quantify regional share or a forecast value.",
        page=8,
    )
    answer = (
        "The regional outlook provides only qualitative direction and does not quantify regional share "
        "or forecast values (page 8, report R-103)."
    )
    result = critic.verify_claims(answer, page8)
    assert result["status"] == "verified", result
    assert len(result["claims"]) == 2
    assert all(claim["pages"] == [8] for claim in result["claims"])


def test_claim_citing_wrong_page_is_rejected_without_llm(monkeypatch):
    monkeypatch.setattr(critic, "_make_model", lambda _p: (_ for _ in ()).throw(AssertionError("must not call critic")))
    result = critic.verify_claims("The report discusses replacement demand (page 5).", evidence(page=4))
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "invalid_citation"


def test_claim_on_a_retrieved_but_irrelevant_page_is_rejected(monkeypatch):
    model = VerdictModel(supported=False)
    mock_critic(monkeypatch, model)
    passages = evidence("The report discusses replacement demand.", 4) + evidence("Distribution channels include retail.", 5)
    result = critic.verify_claims("The report discusses replacement demand (page 5).", passages)
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported"
    prompt = json.loads(model.prompt)
    assert prompt["claims"][0]["cited_evidence"][0]["page"] == 5
    assert "replacement demand" not in prompt["claims"][0]["cited_evidence"][0]["text"]


def test_cross_page_product_term_requires_its_own_citation(monkeypatch):
    # The term is supported on page 4, but the answer cites only page 5.
    # The semantic critic must not be asked to bless evidence outside that cite.
    monkeypatch.setattr(critic, "_make_model", lambda _p: (_ for _ in ()).throw(AssertionError("must reject deterministically")))
    passages = evidence("The report covers point-of-use and point-of-entry filtration.", 4) + evidence(
        "Included products are countertop, under-sink, and whole-home systems.", 5)
    result = critic.verify_claims(
        "The market covers point-of-use and point-of-entry filtration and included products (page 5).",
        passages,
    )
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported_cited_term"


def test_hyphenated_term_is_accepted_when_its_exact_page_is_cited(monkeypatch):
    model = VerdictModel()
    mock_critic(monkeypatch, model)
    passages = evidence("The report covers point-of-use filtration.", 4)
    result = critic.verify_claims("The market covers point-of-use filtration (page 4).", passages)
    assert result["status"] == "verified", result


def test_unsupported_number_is_rejected_by_numeric_guard():
    valid, unsupported = critic.verify_numeric_claims("The market is USD 9.99 billion (page 4).", evidence())
    assert not valid
    assert "9.99" in unsupported


def test_conflicting_passages_follow_conservative_critic_verdict(monkeypatch):
    model = VerdictModel(supported=False)
    mock_critic(monkeypatch, model)
    passages = evidence("The report says demand increased.", 4) + evidence("The report says demand declined.", 5)
    result = critic.verify_claims("Demand increased (page 4).", passages)
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported"


def test_missing_citation_is_insufficient_and_escalates(monkeypatch):
    result = critic.verify_claims("The report discusses replacement demand.", evidence())
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "missing_citation"


def test_verifier_provider_failure_fails_closed(monkeypatch):
    monkeypatch.setattr(critic, "_make_model", lambda _p: SimpleNamespace(invoke=lambda _m: (_ for _ in ()).throw(TimeoutError("secret"))))
    result = critic.verify_claims("The report discusses replacement demand (page 4).", evidence())
    assert result["status"] == "error"
    assert result["reason"] == "timeout"
    assert "secret" not in str(result)


def test_verifier_malformed_response_fails_closed(monkeypatch):
    monkeypatch.setattr(critic, "_make_model", lambda _p: SimpleNamespace(invoke=lambda _m: SimpleNamespace(content="not-json")))
    result = critic.verify_claims("The report discusses replacement demand (page 4).", evidence())
    assert result["status"] == "error"
    assert result["reason"] == "invalid_verifier_response"


def test_agent_escalates_when_claim_review_rejects_draft(monkeypatch, caplog):
    caplog.set_level("INFO", logger="atlas.agent")
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    drafts = iter(["The report is driven by replacement demand (page 4).", "The report is driven by replacement demand (page 4)."])
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": next(drafts)})
    monkeypatch.setattr(agent, "correct_answer", lambda _q, _e, _d, _r: {"answer": next(drafts)})
    monkeypatch.setattr(agent, "verify_claims", lambda _a, _e: {"status": "rejected", "reason": "unsupported_claim", "claims": [{"status": "unsupported_wording"}]})
    result = agent.answer({"question": "What does R-103 say?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    assert result["escalation_reason"] == "Generated claims were not fully supported by their cited report passages."
    assert result["generation_outcome"] == "claim_rejected_after_correction"
    assert "discusses replacement demand" not in result["answer"]
    assert "claim_verification status=rejected" in caplog.text
    assert "unsupported_wording" in caplog.text
    assert "The report is driven" not in caplog.text


def test_agent_returns_supported_r103_summary_after_one_verified_correction(monkeypatch):
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    draft = "The report is driven by replacement demand (page 4)."
    corrected = "The report discusses replacement demand, distribution, and service revenue (page 4)."
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": draft})
    correction_calls = []
    def correct(question, passages, rejected, review):
        correction_calls.append((question, passages, rejected, review))
        return {"answer": corrected}
    monkeypatch.setattr(agent, "correct_answer", correct)
    reviews = iter([
        {"status": "rejected", "reason": "citation_validation_failed", "claims": [{"claim": "driven by replacement demand", "pages": [4], "status": "unsupported_wording"}]},
        {"status": "verified", "reason": None, "claims": [{"claim": "discusses replacement demand, distribution, and service revenue", "pages": [4], "status": "supported"}]},
    ])
    verify_calls = []
    def verify(answer, passages):
        verify_calls.append(answer)
        return next(reviews)
    monkeypatch.setattr(agent, "verify_claims", verify)
    result = agent.answer({"question": "What does R-103 say about demand?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    assert result["answer"] == corrected
    assert len(correction_calls) == 1
    assert verify_calls == [draft, corrected]
    assert result["claim_verification"]["status"] == "verified"
    assert not result.get("escalation_reason")


def test_agent_escalates_if_correction_remains_rejected_without_leaking_drafts(monkeypatch):
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    drafts = iter(["SECRET_REJECTED_ORIGINAL (page 4).", "SECRET_REJECTED_CORRECTION (page 4)."])
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": next(drafts)})
    monkeypatch.setattr(agent, "correct_answer", lambda _q, _e, _d, _r: {"answer": next(drafts)})
    monkeypatch.setattr(agent, "verify_claims", lambda _a, _e: {"status": "rejected", "reason": "unsupported_claim", "claims": [{"status": "unsupported"}]})
    result = agent.answer({"question": "What does R-103 say?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    assert "SECRET_REJECTED" not in result["answer"]
    assert result["generation_outcome"] == "claim_rejected_after_correction"


def test_agent_correction_provider_failure_withholds_rejected_draft(monkeypatch):
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": "SECRET_BAD_DRAFT (page 4)."})
    monkeypatch.setattr(agent, "verify_claims", lambda _a, _e: {"status": "rejected", "reason": "unsupported_claim", "claims": [{"status": "unsupported"}]})
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: (_ for _ in ()).throw(RuntimeError("private provider detail")))
    result = agent.answer({"question": "What does R-103 say?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    assert "SECRET_BAD_DRAFT" not in result["answer"]
    assert "private provider detail" not in str(result)
    assert result["generation_outcome"] == "correction_failed"


def test_insufficient_evidence_never_triggers_correction(monkeypatch):
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": "No supported brand or share found.", "evidence_sufficient": False})
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: (_ for _ in ()).throw(AssertionError("must not retry")))
    result = agent.answer({"question": "Which brand led by what share?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    assert result["generation_outcome"] == "insufficient_evidence"
    assert result["escalation_reason"] == "Retrieved evidence does not support the requested fact."


def test_invalid_citation_can_be_corrected_then_must_pass_verifier(monkeypatch):
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": "The report discusses replacement demand (page 5)."})
    monkeypatch.setattr(agent, "correct_answer", lambda _q, _e, _d, _r: {"answer": "The report discusses replacement demand (page 4)."})
    reviewed = []
    def verify(answer, _evidence):
        reviewed.append(answer)
        if "page 5" in answer:
            return {"status": "rejected", "reason": "citation_validation_failed", "claims": [{"status": "invalid_citation"}]}
        return {"status": "verified", "reason": None, "claims": [{"status": "supported"}]}
    monkeypatch.setattr(agent, "verify_claims", verify)
    result = agent.answer({"question": "What does the report discuss?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    # The numeric/page guard rejects the nonexistent page before semantic
    # review; the corrected answer still receives the full verifier pass.
    assert reviewed == ["The report discusses replacement demand (page 4)."]
    assert result["answer"].endswith("page 4).")
    assert result["claim_verification"]["status"] == "verified"


def test_correction_prompt_uses_only_supplied_retrieved_evidence(monkeypatch):
    captured = {}
    def fake_generate(messages, purpose):
        captured["messages"] = messages
        captured["purpose"] = purpose
        return {"answer": "The report discusses replacement demand (page 4)."}
    monkeypatch.setattr(writer, "_generate", fake_generate)
    writer.correct_answer("What does R-103 say?", evidence(), "bad draft", {
        "claims": [{"claim": "bad phrase", "pages": [4], "status": "unsupported_wording"}],
    })
    prompt = "\n".join(message[1] for message in captured["messages"])
    assert "The report discusses replacement demand." in prompt
    assert captured["purpose"] == "correction"
    assert "When an issue is compound_claim_requires_review" in prompt
    assert "Repeat the subject in each sentence" in prompt
    assert "R-101" not in prompt
    assert "unauthorized private passage" not in prompt


def test_agent_escalates_if_claim_verifier_provider_fails(monkeypatch):
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _q, _e: {"answer": "The report discusses replacement demand (page 4)."})
    monkeypatch.setattr(agent, "verify_claims", lambda _a, _e: {"status": "error", "reason": "timeout", "claims": []})
    result = agent.answer({"question": "What does R-103 say?", "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence()})
    assert result["generation_outcome"] == "claim_verification_failed"
    assert "provider failed" in result["escalation_reason"]
