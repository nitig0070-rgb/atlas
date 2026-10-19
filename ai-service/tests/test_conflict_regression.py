import json
from types import SimpleNamespace

from app import agent, critic
from app.critic import _answer_claims, verify_numeric_claims
from app.rag import REPORT_DIR, parse_report
from app.config import settings


QUESTION = "What was the global smart water meter market size in 2024?"


def conflict_evidence():
    result = []
    for report_id in ("R-101", "R-102"):
        path = next(REPORT_DIR.glob(f"{report_id}_*.md"))
        for chunk in parse_report(path):
            if chunk["page"] in ({8, 9, 11} if report_id == "R-101" else {13, 14, 15}):
                result.append({**chunk, "score": 0.82, "chunk_id": f"{report_id}-{chunk['page']}"})
    return result


def stub_metrics(monkeypatch):
    values = {
        ("R-101", "Market size", "2024"): {
            "value": 4.21, "unit": "USD billion", "scope_note": "Includes hardware, software and services",
        },
        ("R-102", "Market size", "2024"): {
            "value": 3.87, "unit": "USD billion", "scope_note": "AMR / AMI hardware only",
        },
    }
    monkeypatch.setattr(agent, "get_metric", lambda *key: values.get(key))


def test_conflict_answer_keeps_both_values_with_source_page_citations(monkeypatch):
    evidence = conflict_evidence()
    stub_metrics(monkeypatch)
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    # Integration seam: the answer goes through the normal numeric and claim
    # verification loop. The fixture-backed assertions below independently
    # check the exact cited source passage for both values and scope notes.
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {
        "status": "verified", "reason": None, "claims": [{"status": "supported"}],
    })
    result = agent.answer({"question": QUESTION, "allowed": {"R-101", "R-102"},
                           "route": "factual_lookup", "evidence": evidence})

    assert not result.get("escalation_reason")
    assert "USD 4.21 billion" in result["answer"]
    assert "USD 3.87 billion" in result["answer"]
    assert "keep the reported values separate" in result["answer"].lower()
    assert "average" not in result["answer"].lower()
    assert "usd 4.04" not in result["answer"].lower()
    assert "includes hardware, software and services" in result["answer"].lower()
    assert "hardware only" in result["answer"].lower()
    assert "excludes software, installation and recurring services" in result["answer"].lower()
    assert "R-101, page 8" in result["answer"]
    assert "R-102, page 13" in result["answer"]

    evidence_pages = {item["page"] for item in evidence}
    evidence_reports = {item["report_id"] for item in evidence}
    for claim, pages, _unresolved, report_refs in _answer_claims(result["answer"]):
        assert pages, f"Claim has no page citation: {claim}"
        assert report_refs, f"Claim has no report citation: {claim}"
        assert set(pages) <= evidence_pages
        assert report_refs <= evidence_reports

    by_source = {(item["report_id"], item["page"]): item["text"] for item in evidence}
    assert "USD 4.21 billion in 2024" in by_source[("R-101", 8)]
    assert "includes hardware, software and services" in by_source[("R-101", 8)]
    assert "USD 3.87 billion in 2024" in by_source[("R-102", 13)]
    assert "hardware only and excludes software, installation and recurring services" in by_source[("R-102", 13)]
    assert verify_numeric_claims(result["answer"], evidence) == (True, [])
    assert all(not unresolved for _claim, _pages, unresolved, _reports in _answer_claims(result["answer"]))


def test_conflict_answer_uses_cited_scope_inference_not_assistant_process_claim(monkeypatch):
    evidence = conflict_evidence()
    stub_metrics(monkeypatch)
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {
        "status": "verified", "reason": None, "claims": [{"status": "supported"}],
    })

    result = agent.answer({"question": "Compare 2024 global smart water meter market sizes in R-101 and R-102.",
                           "allowed": {"R-101", "R-102"}, "route": "factual_lookup", "evidence": evidence})

    assert not result.get("escalation_reason")
    assert "I have not averaged" not in result["answer"]
    assert "different scopes" in result["answer"].lower()
    assert "keep the reported values separate" in result["answer"].lower()
    assert "average" not in result["answer"].lower()
    assert "R-101, page 8; R-102, page 13" in result["answer"]


def test_critic_prompt_limits_noncomparability_to_cited_scope_differences(monkeypatch):
    evidence = conflict_evidence()
    inspected = {}

    class Model:
        def invoke(self, messages):
            payload = json.loads(messages[1][1])
            inspected["task"] = payload["task"].lower()
            decisions = [{"claim": item["claim"], "supported": True}
                         for item in payload["claims"]]
            return SimpleNamespace(content=json.dumps({"claims": decisions}))

    monkeypatch.setattr(critic, "_make_model", lambda _provider: Model())
    answer = (
        "The reports state different scopes for these figures (R-101, page 8; R-102, page 13). "
        "Keep the reported values separate (R-101, page 8; R-102, page 13)."
    )

    result = critic.verify_claims(answer, evidence)

    assert result["status"] == "verified"
    assert "average figures" in inspected["task"]
    assert "do not infer which figure is more accurate" in inspected["task"]


def test_conflict_correction_cannot_drop_either_report_and_escalates_without_leaking(monkeypatch):
    evidence = conflict_evidence()
    stub_metrics(monkeypatch)
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    reviews = iter([
        {"status": "rejected", "reason": "unsupported_claim",
         "claims": [{"claim": "bad draft", "pages": [8], "status": "unsupported"}]},
        # Even if the semantic critic accepts the correction, the conflict
        # invariant must reject it because it silently lost R-102's side.
        {"status": "verified", "reason": None, "claims": [{"status": "supported"}]},
    ])
    verify_calls = []
    def verify(answer, _evidence):
        verify_calls.append(answer)
        return next(reviews)
    monkeypatch.setattr(agent, "verify_claims", verify)
    monkeypatch.setattr(agent, "correct_answer", lambda *_args: {
        "answer": "R-101 reports USD 4.21 billion in 2024 (R-101, page 8). SECRET_REJECTED_DRAFT"
    })

    result = agent.answer({"question": QUESTION, "allowed": {"R-101", "R-102"},
                           "route": "factual_lookup", "evidence": evidence})
    assert result.get("escalation_reason")
    assert "SECRET_REJECTED_DRAFT" not in result["answer"]
    assert "USD 3.87 billion" not in result["answer"]
    assert len(verify_calls) == 2


def test_missing_conflict_source_page_fails_closed(monkeypatch):
    evidence = [item for item in conflict_evidence()
                if not (item["report_id"] == "R-102" and item["page"] == 13)]
    stub_metrics(monkeypatch)
    result = agent.answer({"question": QUESTION, "allowed": {"R-101", "R-102"},
                           "route": "factual_lookup", "evidence": evidence})
    assert result.get("escalation_reason")
    assert "USD 4.21 billion" not in result["answer"]
    assert "USD 3.87 billion" not in result["answer"]


def test_missing_second_report_does_not_fall_through_to_single_source_answer(monkeypatch):
    evidence = [item for item in conflict_evidence() if item["report_id"] == "R-101"]
    monkeypatch.setattr(agent, "write_answer", lambda *_args: (_ for _ in ()).throw(
        AssertionError("must not answer a two-source comparison from one report")))
    result = agent.answer({"question": QUESTION, "allowed": {"R-101", "R-102"},
                           "route": "factual_lookup", "evidence": evidence})
    assert result["generation_outcome"] == "insufficient_conflict_sources"
    assert result.get("escalation_reason")
    assert "one figure as definitive" in result["answer"]


def test_forecast_period_comparison_extracts_and_cites_each_report(monkeypatch):
    evidence = conflict_evidence()
    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {
        "status": "verified", "reason": None, "claims": [{"status": "supported"} for _ in range(2)],
    })
    question = "Compare the R-101 and R-102 forecast periods."

    result = agent.answer({"question": question, "allowed": {"R-101", "R-102"},
                           "route": "comparison", "evidence": evidence})

    assert not result.get("escalation_reason")
    assert result["generation_outcome"] == "deterministic_forecast_period_comparison"
    assert "2025-2030" in result["answer"]
    assert "2024-2029" in result["answer"]
    assert "R-101, page 11" in result["answer"]
    assert "R-102, page 14" in result["answer"]
    assert verify_numeric_claims(result["answer"], evidence) == (True, [])


def test_forecast_period_comparison_escalates_if_one_source_page_is_missing():
    evidence = [item for item in conflict_evidence()
                if not (item["report_id"] == "R-102" and item["page"] == 14)]
    result = agent.answer({"question": "Compare the R-101 and R-102 forecast periods.",
                           "allowed": {"R-101", "R-102"}, "route": "comparison", "evidence": evidence})

    assert result.get("escalation_reason")
    assert result["generation_outcome"] == "insufficient_forecast_sources"


def test_critic_allows_scope_comparison_only_when_cited_pages_establish_difference(monkeypatch):
    evidence = conflict_evidence()
    inspected = {}

    class Model:
        def invoke(self, messages):
            payload = json.loads(messages[1][1])
            inspected["task"] = payload["task"].lower()
            inspected["claim"] = payload["claims"][0]
            decisions = [{"claim": item["claim"], "supported": True}
                         for item in payload["claims"]]
            return SimpleNamespace(content=json.dumps({"claims": decisions}))

    monkeypatch.setattr(critic, "_make_model", lambda _provider: Model())
    answer = (
        "The reports state different scopes for these figures (R-101, page 8; R-102, page 13). "
        "Keep the reported values separate (R-101, page 8; R-102, page 13)."
    )

    result = critic.verify_claims(answer, evidence)

    assert result["status"] == "verified"
    assert "different scopes" in answer
    assert "cited_evidence" in inspected["task"]
    assert inspected["claim"]["cited_pages"] == [8, 13]
    assert {item["report_id"] for item in inspected["claim"]["cited_evidence"]} == {"R-101", "R-102"}
