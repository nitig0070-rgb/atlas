from app import agent
from app.critic import verify_numeric_claims
from app.rag import REPORT_DIR, parse_report
from app.config import settings
from app.confidence import confidence_components


QUESTION = (
    "What are the main findings of the Residential Water Purifier Market 2025 report (R-103)? "
    "Summarize only findings explicitly supported by retrieved report content and cite relevant pages."
)
EXPECTED_ANSWER = (
    "The report covers point-of-use and point-of-entry household filtration products and discusses "
    "replacement demand, distribution, and service revenue. It provides no global numeric market-size "
    "figure (page 4). Included products are countertop, under-sink, and whole-home residential "
    "purification systems and their original-equipment replacement filters; commercial and municipal "
    "treatment systems are excluded (page 5). Urban households in Asia-Pacific show rising interest in "
    "compact purification systems, but the report provides qualitative direction only and no quantified "
    "regional share or forecast value (page 8). The report uses an illustrative channel survey and analyst "
    "interviews; its sample is not statistically representative, and missing numeric values must not be "
    "inferred (page 10)."
)


def actual_r103_chunks():
    path = next(REPORT_DIR.glob("R-103_*.md"))
    chunks = parse_report(path)
    scores = {4: 0.717438, 8: 0.442741, 5: 0.423157, 10: 0.335845}
    for chunk in chunks:
        chunk["score"] = scores[chunk["page"]]
        chunk["chunk_id"] = f"test-r103-page-{chunk['page']}"
    return sorted(chunks, key=lambda chunk: scores[chunk["page"]], reverse=True)


def test_r103_findings_regression_matches_report_and_stable_confidence(monkeypatch):
    evidence = actual_r103_chunks()
    by_page = {item["page"]: item["text"] for item in evidence}
    assert set(by_page) == {4, 5, 8, 10}

    # Check every factual element in the controlled answer against the actual
    # report text rather than merely checking that citations exist.
    assertions = {
        4: ["point-of-use", "point-of-entry", "replacement demand", "distribution", "service revenue", "No global numeric market-size figure"],
        5: ["countertop", "under-sink", "whole-home", "replacement filters", "Commercial and municipal"],
        8: ["rising interest", "qualitative direction only", "does not quantify"],
        10: ["illustrative channel survey", "analyst interviews", "not statistically representative", "Missing numeric values must not be inferred"],
    }
    for page, phrases in assertions.items():
        source = by_page[page].lower()
        assert all(phrase.lower() in source for phrase in phrases)
    assert "driven by" not in EXPECTED_ANSWER.lower()
    assert verify_numeric_claims(EXPECTED_ANSWER, evidence) == (True, [])

    monkeypatch.setattr(settings, "confidence_threshold", 0.70)
    monkeypatch.setattr(agent, "write_answer", lambda _question, _evidence: {"answer": EXPECTED_ANSWER})
    monkeypatch.setattr(agent, "verify_claims", lambda _answer, _evidence: {"status": "verified", "claims": []})
    state = {"question": QUESTION, "allowed": {"R-103"}, "route": "factual_lookup", "evidence": evidence}
    results = [agent.answer(state) for _ in range(5)]

    expected_citations = [("R-103", page) for page in (4, 8, 5, 10)]
    for result in results:
        assert result["answer"] == EXPECTED_ANSWER
        assert [(c["report_id"], c["page"]) for c in result["citations"]] == expected_citations
        assert result["confidence"] == 0.87
        assert result["confidence_components"]["score"] == result["confidence"]
        assert not result.get("escalation_reason")
        components = result["confidence_components"]
        formula = (0.40 * components["relevance"] + 0.20 * components["support"]
                   + 0.25 * components["citation_coverage"] + 0.10 * components["router_certainty"]
                   + 0.05 * components["calculation_certainty"] - components["conflict_penalty"]
                   - components["ambiguity_penalty"])
        assert result["confidence"] == round(formula, 2)
    assert len({r["confidence"] for r in results}) == 1
    assert len({tuple((c["report_id"], c["page"]) for c in r["citations"]) for r in results}) == 1


def test_reported_88_percent_confidence_is_a_formula_result():
    # This score matches the previously logged 88% run's relevance component;
    # the API computes it from evidence rather than receiving it from Groq.
    evidence = [{"report_id": "R-103", "page": page, "score": 0.7554}
                for page in (4, 5, 8, 10)]
    components = confidence_components(evidence, 4, router_certainty=0.8)
    assert components["relevance"] == 0.8777
    expected = (0.40 * components["relevance"] + 0.20 * components["support"]
                + 0.25 * components["citation_coverage"]
                + 0.10 * components["router_certainty"]
                + 0.05 * components["calculation_certainty"])
    assert components["score"] == round(expected, 2) == 0.88
