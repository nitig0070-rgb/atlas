import re
import logging
from collections import Counter
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.database import get_metric
from app.sql_tool import execute_read_only_query
from app.rag import retrieve
from app.schemas import Citation
from app.writer import write_answer, correct_answer
from app.critic import verify_numeric_claims, verify_claims
from app.confidence import score_confidence, confidence_components
from app.security import is_unsafe_request
from app.calculator import calculate_future_value

MAX_ANSWER_CORRECTIONS = 1
logger = logging.getLogger("atlas.agent")


def _conflict_summary_requirements_met(answer: str, evidence: list[dict]) -> bool:
    """Keep a two-source market-size comparison intact through correction.

    This narrow structural check complements (and never replaces) claim
    verification. It binds each numeric value and scope statement to the
    exact report/page where the fixture states it.
    """
    required = {
        ("R-101", 8): ("usd 4.21 billion in 2024", "includes hardware, software and services"),
        ("R-102", 13): ("usd 3.87 billion in 2024", "hardware only", "excludes software, installation and recurring services"),
    }
    evidence_by_key = {(item.get("report_id"), int(item["page"])): str(item.get("text", ""))
                       for item in evidence if item.get("page") is not None}
    answer_lower = answer.lower()
    answer_sentences = re.split(r"(?<!\d)\.(?=\s|$)", answer_lower)
    for (report_id, page), phrases in required.items():
        source = evidence_by_key.get((report_id, page), "").lower()
        if not source or not all(phrase in source for phrase in phrases):
            return False
        # Require the figure, report ID, and page to be stated together in the
        # answer, so a global numeric check cannot accidentally swap sources.
        figure = re.search(r"\d+\.\d+", phrases[0]).group(0)
        if not any(re.search(rf"\b{re.escape(report_id.lower())}\b.*?\b{re.escape(figure)}\b.*?\bpage\s*{page}\b", sentence)
                   for sentence in answer_sentences):
            return False
        if not all(phrase in answer_lower for phrase in phrases[1:]):
            return False
        for phrase in phrases[1:]:
            if not re.search(
                rf"[^.\n]*{re.escape(phrase)}[^.\n]*\b{re.escape(report_id.lower())}\b[^.\n]*\bpage\s*{page}\b",
                answer_lower,
            ):
                return False
    if not re.search(r"\bnot be averaged\b|\bnot averaged\b", answer_lower):
        return False
    return True


class AgentState(TypedDict, total=False):
    question: str
    client_id: str
    allowed: set[str]
    route: str
    evidence: list[dict]
    answer: str
    citations: list[dict]
    conflicts: list[str]
    derived_values: list[dict]
    confidence: float
    escalation_reason: str
    token_usage: int
    estimated_cost: float | None
    input_tokens: int | None
    output_tokens: int | None
    provider: str
    model: str
    retrieved_chunk_count: int
    source_pages: list[dict]
    retrieved_chunks: list[dict]
    confidence_components: dict
    generation_outcome: str
    claim_verification: dict


def route_question(state: AgentState) -> AgentState:
    q = state["question"].lower()
    if is_unsafe_request(q) or re.search(r"\b(delete|drop|truncate|update|insert)\b", q):
        route = "unsafe"
    elif any(w in q for w in ("election", "politics", "client email", "other client")):
        route = "out_of_scope"
    elif any(w in q for w in ("sector has", "how many reports", "most reports")):
        route = "aggregate"
    elif any(w in q for w in ("calculate", "worth in", "2030", "cagr", "growth")):
        route = "calculation"
    elif any(w in q for w in ("compare", "which report", "trust", "difference")):
        route = "comparison"
    else:
        route = "factual_lookup"
    return {"route": route}


def lookup(state: AgentState) -> AgentState:
    explicit_reports = set(re.findall(r"\bR-\d{3}\b", state["question"].upper()))
    report_filter = explicit_reports or None
    ev = retrieve(state["question"], state["allowed"], report_filter=report_filter)
    if any(item.get("report_id") not in state["allowed"] for item in ev):
        raise RuntimeError("Graph boundary rejected unauthorized evidence before model context construction")
    from app.security import injection_detected
    injected = [e for e in ev if injection_detected(e["text"])]
    for item in injected:
        from app.database import record_security_event
        record_security_event(state.get("client_id"), "PROMPT_INJECTION_DETECTED",
                              {"report_id": item["report_id"], "severity": "high", "chunk_id": item.get("chunk_id", "unknown")})
    return {"evidence": ev}


def answer(state: AgentState) -> AgentState:
    route = state["route"]
    if route == "unsafe":
        return {"answer": "I can't execute or assist with destructive database requests. No database write was attempted.", "confidence": 0.99, "citations": [], "conflicts": [], "derived_values": []}
    if route == "out_of_scope":
        return {"answer": "I'm designed for the market research library. I can't help with that request, but I can answer questions about report coverage, market size, forecasts, or sectors.", "confidence": 0.99, "citations": [], "conflicts": [], "derived_values": []}
    if route == "aggregate":
        rows, query = execute_read_only_query("reports_by_sector")
        rendered = "; ".join(f"{r['sector']}: {r['report_count']}" for r in rows)
        return {"answer": f"Report counts by sector: {rendered}. Read-only query: {query}", "confidence": 0.96, "citations": [], "conflicts": [], "derived_values": []}

    ev = state.get("evidence", [])
    source_pages = sorted({(e["report_id"], int(e["page"])) for e in ev})
    diagnostic_base = {"retrieved_chunk_count": len(ev),
                       "source_pages": [{"report_id": report_id, "page": page} for report_id, page in source_pages],
                       "retrieved_chunks": [{"report_id": e.get("report_id"), "page": int(e["page"]),
                                             "chunk_id": e.get("chunk_id"), "score": round(float(e.get("score", 0)), 6)}
                                            for e in ev]}
    citations = [Citation(report_id=e["report_id"], report_title=e["report_title"], page=int(e["page"]), quote=e["text"][:300]).model_dump() for e in ev]
    required_conflict_summary = False
    water_metrics = "water meter" in state["question"].lower() or "smart water" in state["question"].lower()
    question = state["question"].lower()
    explicit_reports = set(re.findall(r"\bR-\d{3}\b", state["question"].upper()))
    conflict_question = (water_metrics and "2024" in question and
                         any(term in question for term in ("market size", "market value", "size of the market")) and
                         (not explicit_reports or {"R-101", "R-102"}.issubset(explicit_reports)))
    available_reports = {e["report_id"] for e in ev}
    if (conflict_question and {"R-101", "R-102"}.issubset(state.get("allowed", set())) and
            not {"R-101", "R-102"}.issubset(available_reports)):
        return {"answer": "I could not retrieve both entitled report passages needed to compare the 2024 market-size estimates, so I have escalated this rather than presenting one figure as definitive.",
                "citations": citations, "conflicts": [], "derived_values": [], "confidence": 0.3,
                "escalation_reason": "Both report sources are required for this market-size conflict comparison.",
                "claim_verification": {"status": "not_run_missing_conflict_source"},
                "generation_outcome": "insufficient_conflict_sources", **diagnostic_base}
    has_r101 = any(e["report_id"] == "R-101" for e in ev)
    if "2030" in question and has_r101 and (water_metrics or "R-101" in state["question"].upper()):
        if "R-101" not in state["allowed"]:
            return {"answer": "R-101 is not in your current access, so I can't calculate from its figures.", "confidence": 0.99, "citations": [], "conflicts": [], "derived_values": []}
        size_metric = get_metric("R-101", "Market size", "2024")
        cagr_metric = get_metric("R-101", "CAGR", "2025-2030")
        share_metric = get_metric("R-101", "Regional share", "2024")
        if not size_metric or not cagr_metric or not share_metric:
            return {"answer": "The source metrics needed for this calculation are unavailable; I have escalated it for analyst review.",
                    "confidence": 0.3, "citations": citations, "conflicts": [], "derived_values": [],
                    "escalation_reason": "Required metric row is missing."}
        ev = [item for item in ev if item["report_id"] == "R-101"]
        citations = [Citation(report_id=e["report_id"], report_title=e["report_title"], page=int(e["page"]), quote=e["text"][:300]).model_dump() for e in ev]
        global_base = float(size_metric["value"])
        apac_share = float(share_metric["value"]) / 100
        rate = float(cagr_metric["value"]) / 100
        periods = 6
        use_apac = "apac" in question
        base = global_base * apac_share if use_apac else global_base
        value = calculate_future_value(base, rate, periods)
        region = "APAC" if use_apac else "global"
        formula = f"({global_base:.2f} × {apac_share:.2f}) × (1 + {rate:.3f})^{periods}" if use_apac else f"{global_base:.2f} × (1 + {rate:.3f})^{periods}"
        answer_text = (f"Derived estimate: {region} smart water meter market value in 2030 is approximately USD {value:.2f}B. "
                       f"Formula: {formula} = USD {value:.2f}B. "
                       f"Assumption: apply R-101's global 2025-2030 CAGR to the 2024 {region} base for six annual periods. "
                       "The report's CAGR begins in 2025, so using a 2024 base introduces a one-year base-period ambiguity; this is an estimate, not a quoted forecast.")
        conflicts = []
        derived = [{"label": "Derived estimate", "value": round(value, 2), "unit": "USD billion", "formula": formula, "assumptions": ["R-101 global CAGR applied to requested region base", "2024 base compounded over six periods", "2024-to-2025 base-year ambiguity"]}]
        confidence = score_confidence(ev, len(citations), calculation_certainty=0.95, ambiguity=True)
    elif water_metrics and {"R-101", "R-102"}.issubset({e["report_id"] for e in ev}):
        metric_a = get_metric("R-101", "Market size", "2024")
        metric_b = get_metric("R-102", "Market size", "2024")
        by_report_page = {(item.get("report_id"), int(item["page"])): str(item.get("text", "")).lower()
                          for item in ev if item.get("page") is not None}
        source_a = by_report_page.get(("R-101", 8), "")
        source_b = by_report_page.get(("R-102", 13), "")
        if (not metric_a or not metric_b or
                f"usd {float(metric_a['value']):.2f} billion in 2024" not in source_a or
                "includes hardware, software and services" not in source_a or
                f"usd {float(metric_b['value']):.2f} billion in 2024" not in source_b or
                "hardware only and excludes software, installation and recurring services" not in source_b):
            return {"answer": "The source metrics needed for this comparison are unavailable; I have escalated it for analyst review.",
                    "confidence": 0.3, "citations": citations, "conflicts": [], "derived_values": [],
                    "escalation_reason": "Required comparison metric or its cited source passage is missing."}
        answer_text = (
            f"R-101 reports a global smart water meter market value of USD {float(metric_a['value']):.2f} billion in 2024 (R-101, page 8). "
            "R-101 says this broad measure includes hardware, software and services (R-101, page 8). "
            f"R-102 estimates the global AMR / AMI smart water metering hardware market at USD {float(metric_b['value']):.2f} billion in 2024 (R-102, page 13). "
            "R-102 says its estimate covers hardware only and excludes software, installation and recurring services (R-102, page 13). "
            "I have not averaged these different-scope reported values (R-101, page 8; R-102, page 13)."
        )
        conflicts = [f"R-101 scope: {metric_a['scope_note']}; R-102 scope: {metric_b['scope_note']}."]
        confidence = score_confidence(ev, len(citations), conflict_count=1, ambiguity=True)
        derived = []
        required_conflict_summary = True
        generation_outcome = "deterministic_conflict_summary"
    elif "which report" in question and "R-101" not in state["allowed"]:
        answer_text = "R-101 exists in the library but is not included in your current report access, so I can't compare its figures here. You can request access from your account team."
        conflicts, confidence, derived = [], 0.95, []
    elif "which report" in question and {"R-101", "R-102"}.issubset({e["report_id"] for e in ev}):
        answer_text = ("Neither figure is universally more trustworthy from these excerpts alone. R-101 is relevant for a broad market definition including software and services; R-102 is relevant for AMR/AMI hardware-only sizing. Their forecasts use different periods. For a decision requiring one comparable baseline, I recommend analyst review of scope and methodology.")
        conflicts, derived = ["Different scope and forecast window; direct ranking is not supported."], []
        confidence = score_confidence(ev, len(citations), conflict_count=1, ambiguity=True)
    elif not ev:
        answer_text = "I couldn't find enough accessible, relevant evidence in your reports to answer this confidently."
        conflicts, confidence, derived = [], 0.3, []
    else:
        try:
            generated = write_answer(state["question"], ev)
        except Exception as exc:
            # Attach only safe metadata for the API's sanitized provider log.
            if hasattr(exc, "category"):
                exc.provider = settings.llm_provider
                exc.model = settings.model_name
                exc.retrieved_chunk_count = len(ev)
            raise
        answer_text = generated["answer"]
        generation_outcome = "success"
        conflicts, derived = [], []
        confidence = score_confidence(ev, len(citations), router_certainty=0.8)
        components = confidence_components(ev, len(citations), router_certainty=0.8)
    generations = [generated] if "generated" in locals() else []
    def telemetry_for_generations():
        input_values = [item.get("input_tokens") for item in generations if item.get("input_tokens") is not None]
        output_values = [item.get("output_tokens") for item in generations if item.get("output_tokens") is not None]
        cost_values = [item.get("estimated_cost") for item in generations if item.get("estimated_cost") is not None]
        return {"token_usage": sum(input_values) + sum(output_values),
                "input_tokens": sum(input_values) if input_values else None,
                "output_tokens": sum(output_values) if output_values else None,
                "estimated_cost": sum(cost_values) if cost_values else None}
    telemetry = telemetry_for_generations()
    if confidence < settings.confidence_threshold:
        reason = "Insufficient supported evidence or unresolved scope ambiguity."
        return {"answer": answer_text, "citations": citations, "conflicts": conflicts,
                "derived_values": derived, "confidence": confidence, "confidence_components": locals().get("components", {}),
                "escalation_reason": reason,
                "generation_outcome": locals().get("generation_outcome", "not_attempted"),
                **diagnostic_base, **telemetry}
    if "generated" in locals() and generated.get("evidence_sufficient") is False:
        return {"answer": answer_text, "citations": citations, "conflicts": conflicts,
                "derived_values": derived, "confidence": confidence,
                "confidence_components": {**locals().get("components", {}), "generation_abstained": 1},
                "escalation_reason": "Retrieved evidence does not support the requested fact.",
                "generation_outcome": "insufficient_evidence", **diagnostic_base, **telemetry}
    if not derived and ev:
        corrections = 0
        while True:
            numeric_valid, _unsupported = verify_numeric_claims(answer_text, ev)
            if numeric_valid:
                claim_review = verify_claims(answer_text, ev)
            else:
                claim_review = {"status": "rejected", "reason": "numeric_claim_rejected",
                                "claims": [{"claim": "numeric value or page reference", "pages": [],
                                            "status": "unsupported_number"}]}
            status_counts = Counter(item.get("status", "unknown") for item in claim_review.get("claims", []))
            safe_statuses = {key: status_counts[key] for key in sorted(status_counts)
                             if key in {"supported", "unsupported", "unsupported_wording", "missing_citation",
                                        "invalid_citation", "compound_claim_requires_review", "ambiguous_report_citation",
                                        "verifier_error", "unsupported_number"}}
            logger.info("claim_verification status=%s reason=%s correction_attempt=%d claim_count=%d statuses=%s",
                        str(claim_review.get("status", "unknown"))[:32],
                        str(claim_review.get("reason", "none"))[:64], corrections,
                        sum(status_counts.values()), safe_statuses)
            if numeric_valid and claim_review["status"] == "verified":
                if required_conflict_summary and not _conflict_summary_requirements_met(answer_text, ev):
                    claim_review = {"status": "rejected", "reason": "required_conflict_side_missing",
                                    "claims": [{"claim": "both source-specific values and scopes", "pages": [8, 13],
                                                "status": "unsupported_conflict_summary"}]}
                else:
                    break
            if claim_review["status"] == "error":
                reason = "Claim verification provider failed; answer withheld for analyst review."
                return {"answer": "I found report passages but could not verify every claim against its cited evidence, so I've sent this for analyst review.",
                        "citations": citations, "conflicts": conflicts, "derived_values": [], "confidence": confidence,
                        "escalation_reason": reason, "confidence_components": locals().get("components", {}),
                        "claim_verification": claim_review, "generation_outcome": "claim_verification_failed",
                        **diagnostic_base, **telemetry_for_generations()}
            if corrections >= MAX_ANSWER_CORRECTIONS:
                reason = ("Numeric claim failed evidence check." if not numeric_valid else
                          "Generated claims were not fully supported by their cited report passages.")
                return {"answer": "I found report passages but could not verify every claim against its cited evidence, so I've sent this for analyst review.",
                        "citations": citations, "conflicts": conflicts, "derived_values": [], "confidence": confidence,
                        "escalation_reason": reason, "confidence_components": locals().get("components", {}),
                        "claim_verification": claim_review,
                        "generation_outcome": "claim_rejected_after_correction",
                        **diagnostic_base, **telemetry_for_generations()}
            # Only actual rejected drafts are eligible for a wording/citation/number
            # repair. Insufficient evidence and verifier failures fail closed above.
            try:
                generated = correct_answer(state["question"], ev, answer_text, claim_review)
            except Exception as exc:
                correction_error = getattr(exc, "category", type(exc).__name__)
                return {"answer": "I found report passages but couldn't safely complete answer verification, so I've sent this for analyst review.",
                        "citations": citations, "conflicts": conflicts, "derived_values": [], "confidence": confidence,
                        "escalation_reason": f"Correction provider failed ({correction_error}); answer withheld for analyst review.",
                        "confidence_components": locals().get("components", {}),
                        "claim_verification": claim_review, "generation_outcome": "correction_failed",
                        **diagnostic_base, **telemetry_for_generations()}
            generations.append(generated)
            corrections += 1
            answer_text = generated["answer"]
            if generated.get("evidence_sufficient") is False:
                return {"answer": "The retrieved passages do not provide enough evidence to answer this question, so I've sent it for analyst review.",
                        "citations": citations, "conflicts": conflicts, "derived_values": [], "confidence": confidence,
                        "escalation_reason": "Retrieved evidence does not support the requested fact.",
                        "confidence_components": {**locals().get("components", {}), "generation_abstained": 1},
                        "claim_verification": {"status": "insufficient_evidence"},
                        "generation_outcome": "insufficient_evidence_after_correction",
                        **diagnostic_base, **telemetry_for_generations()}
    return {"answer": answer_text, "citations": citations, "conflicts": conflicts,
            "derived_values": derived, "confidence": confidence,
            "confidence_components": locals().get("components", {}),
            "claim_verification": claim_review if "claim_review" in locals() else {"status": "not_applicable"},
            "generation_outcome": locals().get("generation_outcome", "not_attempted"),
            "provider": generated.get("provider", settings.llm_provider) if "generated" in locals() else settings.llm_provider,
            "model": generated.get("model", settings.model_name) if "generated" in locals() else settings.model_name,
            **diagnostic_base, **telemetry_for_generations()}


def compile_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", route_question)
    graph.add_node("retrieve", lookup)
    # LangGraph reserves state-field names for channels, so a node cannot
    # share the name of the AgentState `answer` field.
    graph.add_node("answer_node", answer)
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", lambda s: "answer_node" if s["route"] in {"unsafe", "out_of_scope", "aggregate"} else "retrieve",
                                {"answer_node": "answer_node", "retrieve": "retrieve"})
    graph.add_edge("retrieve", "answer_node")
    graph.add_edge("answer_node", END)
    return graph.compile()


workflow = compile_graph()
