from app import agent
from app.critic import _answer_claims, verify_numeric_claims
from app.rag import REPORT_DIR, parse_report
from app.config import settings


QUESTION = "What was the global smart water meter market size in 2024?"


def conflict_evidence():
    result = []
    for report_id in ("R-101", "R-102"):
        path = next(REPORT_DIR.glob(f"{report_id}_*.md"))
        for chunk in parse_report(path):
            if chunk["page"] in ({8, 9} if report_id == "R-101" else {13, 15}):
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
    assert "not averaged" in result["answer"].lower()
    assert "average" not in result["answer"].lower().replace("not averaged", "")
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
