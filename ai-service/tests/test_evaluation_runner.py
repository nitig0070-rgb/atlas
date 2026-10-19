from evaluation.runner import evaluate_case, http_failure_result, summarize


def test_case_metrics_check_report_coverage_and_sensitive_output():
    case = {"id": "T01", "category": "entitlement", "expected_reports": ["R-101"],
            "expected_escalated": True,
            "must_not_contain": ["4.21"]}
    answer = {"answer": "R-101 is not accessible.",
              "citations": [{"report_id": "R-101", "page": 8}],
              "confidence": 0.9, "escalated": True, "token_usage": 12,
              "estimated_cost": 0.0002}

    result = evaluate_case(case, answer, latency_ms=8.125)

    assert result["failures"] == []
    assert result["citation_report_coverage"] == 1.0
    assert result["latency_ms"] == 8.12
    assert result["escalated"] is True
    assert result["checks"]["escalation_policy_match"] is True
    assert result["request_id"] is None


def test_successful_evaluation_retains_api_request_id():
    case = {"id": "T05", "category": "factual", "expected_reports": [], "must_not_contain": []}
    result = evaluate_case(case, {"answer": "Supported.", "citations": [], "request_id": "req-safe-id"})
    assert result["request_id"] == "req-safe-id"


def test_http_429_evaluation_result_retains_api_request_id():
    case = {"id": "T06", "category": "factual", "expected_reports": ["R-103"]}
    result = http_failure_result(case, status_code=429, latency_ms=8.5, request_id="req-rate-limited")
    assert result["http"] == 429
    assert result["failures"] == ["http_success"]
    assert result["request_id"] == "req-rate-limited"


def test_aggregate_library_fixture_does_not_require_content_citations():
    from json import loads
    from pathlib import Path

    cases = loads((Path(__file__).parents[1] / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    case = next(item for item in cases if item["id"] == "E19")
    assert case["category"] == "aggregate"
    assert case["expected_reports"] == []


def test_summary_reports_failures_metrics_and_category_breakdown():
    results = [
        {"id": "T01", "category": "factual", "checks": {"http_success": True, "safety_pass": True},
         "failures": [], "expected_reports": ["R-101"], "cited_reports": ["R-101"],
         "latency_ms": 10, "escalated": False, "token_usage": 30, "estimated_cost": None},
        {"id": "T02", "category": "entitlement", "checks": {"http_success": True, "safety_pass": False},
         "failures": ["safety_pass", "expected_reports_present"], "expected_reports": ["R-103"],
         "cited_reports": [], "latency_ms": 30, "escalated": True,
         "token_usage": None, "estimated_cost": None},
        {"id": "T03", "category": "network", "checks": {"http_success": False},
         "failures": ["request_error"], "expected_reports": ["R-104"], "cited_reports": [],
         "latency_ms": None, "escalated": None},
    ]

    result = summarize(results)

    assert result["overall"]["cases"] == 3
    assert result["overall"]["http_success_rate"] == 2 / 3
    assert result["overall"]["safety_pass_rate"] == 0.5
    assert result["overall"]["safety_checked_cases"] == 2
    assert result["overall"]["expected_report_coverage"] == 1 / 3
    assert result["overall"]["mean_latency_ms"] == 20
    assert result["overall"]["p95_latency_ms"] == 30
    assert result["overall"]["token_usage_total"] == 30
    assert result["overall"]["token_usage_reported_cases"] == 1
    assert result["overall"]["failed_case_ids"] == ["T02", "T03"]
    assert result["by_category"]["entitlement"]["escalations"] == 1
    assert result["failures"][0]["reasons"] == ["safety_pass", "expected_reports_present"]


def test_empty_evaluation_summary_has_null_rates():
    result = summarize([])
    assert result["overall"]["cases"] == 0
    assert result["overall"]["http_success_rate"] is None
    assert result["overall"]["expected_report_coverage"] is None


def test_expected_escalation_policy_is_counted_only_when_configured():
    case = {"id": "T04", "category": "unsupported", "expected_reports": [],
            "expected_escalated": True, "must_not_contain": []}
    result = evaluate_case(case, {"answer": "Insufficient evidence.", "citations": [], "escalated": False})

    assert result["checks"]["escalation_policy_match"] is False
    assert result["failures"] == ["escalation_policy_match"]
