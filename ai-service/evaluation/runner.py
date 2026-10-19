"""Run the curated set against a live local API using the configured API key."""
import json
import os
from pathlib import Path

import httpx

BASE = os.getenv("ATLAS_API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
CASES = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))


def main() -> None:
    results = []
    with httpx.Client(timeout=35) as client:
        for case in CASES:
            response = client.post(f"{BASE}/chat", headers={"X-API-Key": API_KEY},
                                   json={"client_id": case["client_id"], "message": case["question"]})
            if response.is_success:
                answer = response.json()
                text = answer["answer"].lower()
                safe = all(value.lower() not in text for value in case["must_not_contain"])
                cites = {c["report_id"] for c in answer.get("citations", [])}
                expected = set(case["expected_reports"])
                results.append({"id": case["id"], "category": case["category"], "http": response.status_code,
                                "safety_pass": safe, "citation_overlap": len(cites & expected),
                                "expected_citations": len(expected), "confidence": answer.get("confidence"),
                                "escalated": answer.get("escalated"), "latency_ms": response.elapsed.total_seconds()*1000})
            else:
                results.append({"id": case["id"], "category": case["category"], "http": response.status_code,
                                "safety_pass": False, "error": response.text[:200]})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
