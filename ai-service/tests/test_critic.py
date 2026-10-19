from app.critic import verify_numeric_claims
from app.confidence import score_confidence


def test_numeric_claim_must_appear_in_evidence():
    evidence = [{"text": "Market value was USD 4.21 billion in 2024."}]
    assert verify_numeric_claims("USD 4.21 billion in 2024", evidence)[0]
    assert not verify_numeric_claims("USD 9.99 billion in 2024", evidence)[0]


def test_numeric_check_accepts_equivalent_number_formatting_and_units():
    evidence = [{"text": "Revenue was USD 4.21 billion and CAGR reached 9.8 percent."}]
    assert verify_numeric_claims("Revenue was USD 4.21B and CAGR reached 9.8%.", evidence)[0]


def test_numeric_check_does_not_treat_report_id_as_a_factual_number():
    evidence = [{"text": "Residential systems include countertop and under-sink models."}]
    assert verify_numeric_claims("R-103 covers countertop and under-sink models.", evidence)[0]


def test_numeric_check_ignores_model_line_citations_and_validates_page_metadata():
    evidence = [
        {"text": "Countertop and under-sink systems are included.", "page": 4},
        {"text": "Whole-home systems and replacement filters are included.", "page": 5},
    ]
    answer = "R‑103 includes these products (page 5; page 4). 【5†L1-L4】【4†L1-L3】"
    assert verify_numeric_claims(answer, evidence) == (True, [])


def test_numeric_check_accepts_report_year_from_retrieved_title_metadata():
    evidence = [{"report_id": "R-103", "report_title": "Residential Water Purifier Market 2025",
                 "year": 2025, "page": 4, "text": "No global numeric market-size figure is provided."}]
    assert verify_numeric_claims("The 2025 report does not provide a global market-size figure (page 4).", evidence) == (True, [])
    valid, unsupported = verify_numeric_claims("The source is on page 99.", evidence)
    assert not valid
    assert "page:99" in unsupported


def test_confidence_penalizes_conflict_and_ambiguity():
    evidence = [{"report_id": "R-101", "score": 0.8}, {"report_id": "R-102", "score": 0.8}]
    clear = score_confidence(evidence, 2)
    uncertain = score_confidence(evidence, 2, conflict_count=1, ambiguity=True)
    assert uncertain < clear


def test_confidence_accepts_one_report_with_multiple_supporting_pages():
    evidence = [
        {"report_id": "R-103", "page": 4, "score": 0.75},
        {"report_id": "R-103", "page": 5, "score": 0.61},
    ]
    assert score_confidence(evidence, 2, router_certainty=0.8) >= 0.70
