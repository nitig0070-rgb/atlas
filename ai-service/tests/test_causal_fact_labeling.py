import json
from pathlib import Path
from types import SimpleNamespace

from app import agent, critic
from app.critic import _answer_claims, _wording_strength_supported, verify_numeric_claims
from app.rag import parse_report
from app.writer import build_messages


REPORT = Path(__file__).resolve().parents[1] / "data" / "reports" / "R-103_water_purifier_2025.md"


def r103_evidence():
    chunks = parse_report(REPORT)
    return [{**chunk, "score": 0.75} for chunk in chunks if chunk["page"] in {4, 8}]


def approve_claims(monkeypatch):
    class Model:
        def invoke(self, messages):
            payload = json.loads(messages[1][1])
            claims = [{"claim": item["claim"], "supported": True} for item in payload["claims"]]
            return SimpleNamespace(content=json.dumps({"claims": claims}))

    monkeypatch.setattr(critic, "_make_model", lambda _provider: Model())


def test_discussed_topic_is_not_accepted_as_an_asserted_market_driver(monkeypatch):
    evidence = r103_evidence()
    page4 = next(item["text"] for item in evidence if item["page"] == 4)
    assert "discusses replacement demand" in page4.lower()
    approve_claims(monkeypatch)

    result = critic.verify_claims(
        "Replacement demand is a key driver of the market (R-103, page 4).", evidence
    )
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported_wording"


def test_live_style_driver_claims_for_each_discussed_topic_are_rejected(monkeypatch):
    evidence = r103_evidence()
    monkeypatch.setattr(critic, "_make_model", lambda _provider: (_ for _ in ()).throw(
        AssertionError("unsupported causal wording should fail before semantic review")))
    answer = (
        "The report states that replacement demand is a driver of the market (R-103, page 4). "
        "The report states that distribution is a driver of the market (R-103, page 4). "
        "The report states that service revenue is a driver of the market (R-103, page 4)."
    )

    result = critic.verify_claims(answer, evidence)

    assert result["status"] == "rejected"
    assert len(result["claims"]) == 3
    assert all(claim["status"] == "unsupported_wording" for claim in result["claims"])


def test_cautious_statement_that_source_does_not_establish_causation_is_reviewable(monkeypatch):
    evidence = r103_evidence()
    approve_claims(monkeypatch)
    claim = "The report does not establish that replacement demand drives market growth (R-103, page 4)."

    result = critic.verify_claims(claim, evidence)
    assert result["status"] == "verified", result
    parsed = _answer_claims(claim)
    assert parsed[0][1] == [4]
    assert parsed[0][3] == {"R-103"}


def test_cautious_but_unsupported_causal_claim_is_rejected_by_critic(monkeypatch):
    evidence = r103_evidence()

    class RejectingModel:
        def invoke(self, messages):
            payload = json.loads(messages[1][1])
            # Simulate the semantic critic finding that the claim's assertion
            # is unsupported; cautious framing must not override that verdict.
            claims = [{"claim": item["claim"], "supported": False}
                      for item in payload["claims"]]
            return SimpleNamespace(content=json.dumps({"claims": claims}))

    monkeypatch.setattr(critic, "_make_model", lambda _provider: RejectingModel())
    result = critic.verify_claims(
        "The report does not establish that replacement demand drives market growth (R-103, page 4).",
        evidence,
    )

    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "unsupported"


def test_causal_question_prompt_requires_fact_and_inference_labels_and_preserves_qualifiers():
    question = (
        "What factors drive this market? Distinguish directly reported facts from inference."
    )
    prompt = build_messages(question, r103_evidence())[0][1].lower()
    assert "reported facts" in prompt
    assert "inference" in prompt
    assert "causal wording in the question" in prompt
    assert "unproven premise" in prompt
    assert "discusses" in prompt and "does not establish" in prompt
    assert "qualitative" in prompt and "quantified" in prompt
    assert "report id" in prompt and "exact page" in prompt


def test_qualitative_r103_page8_does_not_support_a_number_or_forecast():
    evidence = r103_evidence()
    page8 = next(item["text"] for item in evidence if item["page"] == 8).lower()
    assert "rising interest" in page8
    assert "qualitative direction only" in page8
    assert "does not quantify regional share or a forecast value" in page8
    answer = "Asia-Pacific share is 41% in 2025 (R-103, page 8)."
    assert verify_numeric_claims(answer, evidence) == (False, ["41"])


def test_r103_report_page_citation_is_bound_to_exact_retrieved_page(monkeypatch):
    evidence = r103_evidence()
    page4 = next(item["text"] for item in evidence if item["page"] == 4)
    assert "replacement demand" in page4.lower()
    monkeypatch.setattr(critic, "_make_model", lambda _provider: (_ for _ in ()).throw(
        AssertionError("a wrong page must be rejected before semantic verification")))

    result = critic.verify_claims(
        "The report discusses replacement demand (R-103, page 5).", evidence
    )
    assert result["status"] == "rejected"
    assert result["claims"][0]["status"] == "invalid_citation"


def test_wording_strength_recognizes_driver_claims_and_cautious_negation():
    page4 = "The report discusses replacement demand, distribution, and service revenue."
    assert not _wording_strength_supported("Replacement demand is a key driver", [page4])
    assert not _wording_strength_supported("Replacement demand drives market growth", [page4])
    assert _wording_strength_supported(
        "The report does not establish that replacement demand drives market growth", [page4]
    )
    assert not _wording_strength_supported(
        "The report does not establish causation, but replacement demand drives market growth", [page4]
    )


def test_agent_corrects_missing_fact_inference_labels_and_reverifies(monkeypatch):
    evidence = r103_evidence()
    question = "What product categories does the report cover? Distinguish directly reported facts from any inference."
    draft = "The report discusses replacement demand (R-103, page 4)."
    corrected = (
        "Reported facts: R-103 discusses replacement demand, distribution, and service revenue (R-103, page 4). "
        "R-103 reports rising interest among urban Asia-Pacific households in compact purification systems (R-103, page 8). "
        "R-103 says the regional evidence is qualitative and does not quantify regional share or a forecast (R-103, page 8). "
        "Inference: The cited passages do not establish that these topics cause market growth (R-103, page 4; R-103, page 8)."
    )
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda *_args: {"answer": draft})
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: {"answer": corrected})
    verified = []
    monkeypatch.setattr(agent, "verify_claims", lambda answer, _evidence: (
        verified.append(answer) or {"status": "verified", "reason": None, "claims": [{"status": "supported"}]}
    ))

    result = agent.answer({"question": question, "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence})
    assert result["answer"] == corrected
    assert verified == [draft, corrected]
    assert result["claim_verification"]["status"] == "verified"
    assert not result.get("escalation_reason")


def test_agent_escalates_if_fact_inference_labels_remain_missing(monkeypatch):
    evidence = r103_evidence()
    question = "Distinguish the reported facts from inference about market drivers."
    draft = "The report discusses replacement demand (R-103, page 4)."
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda *_args: {"answer": draft})
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: {"answer": draft})
    reviews = iter([
        {"status": "verified", "reason": None, "claims": [{"status": "supported"}]},
        {"status": "rejected", "reason": "unsupported_claim", "claims": [{"status": "unsupported"}]},
    ])
    monkeypatch.setattr(agent, "verify_claims", lambda *_args: next(reviews))

    result = agent.answer({"question": question, "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence})
    assert result.get("escalation_reason")
    assert result["generation_outcome"] == "claim_rejected_after_correction"
    assert result["answer"] != draft


def test_agent_does_not_return_labeled_answer_when_critic_rejects_claim(monkeypatch):
    evidence = r103_evidence()
    question = "Distinguish reported facts from inference about market drivers."
    draft = (
        "Reported facts: R-103 discusses replacement demand (R-103, page 4). "
        "Inference: Replacement demand drives market growth (R-103, page 4)."
    )
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda *_args: {"answer": draft})
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: {"answer": draft})

    def reject_causal_claim(answer, _evidence):
        if "drives market growth" in answer or "causal relationship" in answer:
            return {"status": "rejected", "reason": "unsupported_claim",
                    "claims": [{"status": "unsupported"}]}
        return {"status": "verified", "reason": None,
                "claims": [{"status": "supported"}]}

    monkeypatch.setattr(agent, "verify_claims", reject_causal_claim)
    result = agent.answer({"question": question, "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence})

    assert result.get("escalation_reason")
    assert result["generation_outcome"] == "claim_rejected_after_correction"
    assert result["answer"] != draft


def test_agent_uses_cited_extracts_as_single_bounded_correction_for_requested_labels(monkeypatch):
    evidence = r103_evidence()
    question = "What drives the market? Distinguish reported facts from inference."
    rejected = "Replacement demand drives market growth."
    verification_inputs = []
    reviews = iter([
        {"status": "rejected", "reason": "citation_validation_failed",
         "claims": [{"status": "missing_citation"}]},
        {"status": "verified", "reason": None,
         "claims": [{"status": "supported"} for _ in range(8)]},
    ])
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda *_args: {"answer": rejected})
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: (_ for _ in ()).throw(
        AssertionError("labelled correction must use exact retrieved sentences, not another provider draft")))

    def verify(answer, _evidence):
        verification_inputs.append(answer)
        return next(reviews)

    monkeypatch.setattr(agent, "verify_claims", verify)
    result = agent.answer({"question": question, "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence})

    assert not result.get("escalation_reason")
    assert result["generation_outcome"] == "evidence_only_correction"
    assert "Reported facts:" in result["answer"]
    assert "Inference:" in result["answer"]
    assert "The report discusses replacement demand, distribution, and service revenue (R-103, page 4)." in result["answer"]
    assert "(R-103, page 4)" in result["answer"]
    assert "(R-103, page 8)" in result["answer"]
    assert "drives market growth" not in result["answer"].lower()
    assert rejected not in result["answer"]
    for claim, pages, _unresolved, reports in _answer_claims(result["answer"]):
        assert pages, f"Fallback claim has no citation: {claim}"
        assert reports == {"R-103"}
    assert verification_inputs[0] == rejected
    assert "Inference:" in verification_inputs[1]


def test_writer_abstention_uses_one_verified_extract_fallback_for_causal_distinction(monkeypatch):
    evidence = r103_evidence()
    question = (
        "According to report R-103, what factors drive the residential water purifier market? "
        "Distinguish directly reported facts from any inference."
    )
    monkeypatch.setattr(agent.settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda *_args: {
        "answer": "I do not have enough evidence.", "evidence_sufficient": False,
    })
    verification_inputs = []

    def verify(answer, _evidence):
        verification_inputs.append(answer)
        claims = [{"status": "supported"} for _ in _answer_claims(answer)]
        return {"status": "verified", "reason": None, "claims": claims}

    monkeypatch.setattr(agent, "verify_claims", verify)
    result = agent.answer({"question": question, "allowed": {"R-103"},
                           "route": "factual_lookup", "evidence": evidence})

    assert not result.get("escalation_reason")
    assert result["generation_outcome"] == "evidence_only_correction"
    assert result["claim_verification"]["status"] == "verified"
    assert len(verification_inputs) == 1
    assert "Reported facts:" in result["answer"]
    assert "Inference:" in result["answer"]
    assert "discusses replacement demand, distribution, and service revenue (R-103, page 4)" in result["answer"]
    assert "drives market growth" not in result["answer"].lower()
