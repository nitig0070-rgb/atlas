"""Run the curated evaluation set against a live local API.

Report citation overlap and operational/safety checks only. These metrics are
not a substitute for human review of factual accuracy or citation entailment.
"""
import json
import os
import statistics
import time
from pathlib import Path

import httpx

BASE = os.getenv("ATLAS_API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
CASES = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))


def evaluate_case(case: dict, answer: dict, *, status_code: int = 200,
                  latency_ms: float = 0.0) -> dict:
    """Score deterministic harness checks for one successful API response."""
    text = str(answer.get("answer", "")).lower()
    expected_reports = set(case.get("expected_reports", []))
    cited_reports = {str(item.get("report_id")) for item in answer.get("citations", [])
                     if item.get("report_id")}
    safety_pass = all(str(value).lower() not in text for value in case.get("must_not_contain", []))
    report_coverage = (len(expected_reports & cited_reports) / len(expected_reports)
                       if expected_reports else 1.0)
    checks = {
        "http_success": 200 <= status_code < 300,
        "safety_pass": safety_pass,
        "expected_reports_present": expected_reports <= cited_reports,
    }
    if isinstance(case.get("expected_escalated"), bool):
        checks["escalation_policy_match"] = answer.get("escalated") is case["expected_escalated"]
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "id": case["id"], "category": case["category"], "http": status_code,
        "checks": checks, "failures": failures,
        "request_id": answer.get("request_id"),
        "citation_report_coverage": report_coverage,
        "expected_reports": sorted(expected_reports), "cited_reports": sorted(cited_reports),
        "confidence": answer.get("confidence"), "escalated": answer.get("escalated"),
        "latency_ms": round(float(latency_ms), 2),
        "token_usage": answer.get("token_usage"),
        "estimated_cost": answer.get("estimated_cost"),
    }


def _metrics(results: list[dict]) -> dict:
    total = len(results)
    http_ok = sum(bool(row.get("checks", {}).get("http_success")) for row in results)
    safety_rows = [row for row in results if "safety_pass" in row.get("checks", {})]
    safety_ok = sum(bool(row["checks"]["safety_pass"]) for row in safety_rows)
    escalation_rows = [row for row in results if "escalation_policy_match" in row.get("checks", {})]
    escalation_ok = sum(bool(row["checks"]["escalation_policy_match"]) for row in escalation_rows)
    expected = sum(len(row.get("expected_reports", [])) for row in results)
    covered = sum(len(set(row.get("expected_reports", [])) & set(row.get("cited_reports", [])))
                  for row in results)
    latencies = sorted(float(row["latency_ms"]) for row in results
                       if isinstance(row.get("latency_ms"), (int, float)))
    tokens = [row["token_usage"] for row in results if isinstance(row.get("token_usage"), (int, float))]
    costs = [row["estimated_cost"] for row in results
             if isinstance(row.get("estimated_cost"), (int, float))]
    p95_index = max(0, int(0.95 * len(latencies) + 0.999999) - 1) if latencies else 0
    return {
        "cases": total,
        "http_success_rate": http_ok / total if total else None,
        "safety_pass_rate": safety_ok / len(safety_rows) if safety_rows else None,
        "safety_checked_cases": len(safety_rows),
        "escalation_policy_match_rate": escalation_ok / len(escalation_rows) if escalation_rows else None,
        "escalation_policy_checked_cases": len(escalation_rows),
        "expected_report_coverage": covered / expected if expected else None,
        "mean_latency_ms": round(statistics.fmean(latencies), 2) if latencies else None,
        "p95_latency_ms": round(latencies[p95_index], 2) if latencies else None,
        "escalations": sum(row.get("escalated") is True for row in results),
        "token_usage_total": sum(tokens) if tokens else None,
        "token_usage_reported_cases": len(tokens),
        "estimated_cost_total": round(sum(costs), 8) if costs else None,
        "estimated_cost_reported_cases": len(costs),
        "failed_case_ids": [row["id"] for row in results if row.get("failures")],
    }


def summarize(results: list[dict]) -> dict:
    """Return overall and per-category check metrics plus actionable failures."""
    grouped: dict[str, list[dict]] = {}
    for row in results:
        grouped.setdefault(row.get("category", "uncategorized"), []).append(row)
    return {
        "overall": _metrics(results),
        "by_category": {category: _metrics(rows) for category, rows in sorted(grouped.items())},
        "failures": [{"id": row["id"], "category": row.get("category"),
                      "reasons": row.get("failures", [])}
                     for row in results if row.get("failures")],
    }


def http_failure_result(case: dict, *, status_code: int | None, latency_ms: float | None,
                        request_id: str | None = None, error_type: str | None = None) -> dict:
    result = {
        "id": case["id"], "category": case["category"], "http": status_code,
        "checks": {"http_success": False},
        "failures": ["http_success" if status_code is not None else "request_error"],
        "expected_reports": case.get("expected_reports", []), "cited_reports": [],
        "latency_ms": round(float(latency_ms), 2) if latency_ms is not None else None,
        "request_id": request_id,
    }
    if error_type:
        result["error_type"] = error_type
    return result


def main() -> None:
    results = []
    import sys
    with httpx.Client(timeout=60) as client:
        for case in CASES:
            for attempt in range(12):
                try:
                    response = client.post(f"{BASE}/chat", headers={"X-API-Key": API_KEY},
                                           json={"client_id": case["client_id"], "message": case["question"]})
                    latency_ms = response.elapsed.total_seconds() * 1000
                    if response.status_code == 429 and attempt < 11:
                        retry_after = response.headers.get("Retry-After")
                        wait_seconds = int(retry_after) + 2 if retry_after and retry_after.isdigit() else 12 * (attempt + 1)
                        sys.stderr.write(f"[{case['id']}] Rate limited (429). Retrying in {wait_seconds}s (attempt {attempt + 1}/11)...\n")
                        sys.stderr.flush()
                        time.sleep(wait_seconds)
                        continue
                    if response.is_success:
                        results.append(evaluate_case(case, response.json(),
                                                     status_code=response.status_code,
                                                     latency_ms=latency_ms))
                    else:
                        results.append(http_failure_result(
                            case, status_code=response.status_code, latency_ms=latency_ms,
                            request_id=response.headers.get("X-Request-ID")))
                    sys.stderr.write(f"[{case['id']}] Completed with status {response.status_code} in {latency_ms:.0f}ms\n")
                    sys.stderr.flush()
                    break
                except httpx.HTTPError as exc:
                    if attempt < 5:
                        sys.stderr.write(f"[{case['id']}] HTTP error {type(exc).__name__}. Retrying in {5 * (attempt + 1)}s...\n")
                        sys.stderr.flush()
                        time.sleep(5 * (attempt + 1))
                        continue
                    results.append(http_failure_result(case, status_code=None, latency_ms=None,
                                                       error_type=type(exc).__name__))
                    sys.stderr.write(f"[{case['id']}] Failed after retries: {type(exc).__name__}\n")
                    sys.stderr.flush()
                    break
            time.sleep(2.0)
    print(json.dumps({"summary": summarize(results), "case_results": results}, indent=2))


if __name__ == "__main__":
    main()
