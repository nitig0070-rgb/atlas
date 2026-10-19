def score_confidence(
    evidence: list[dict],
    citation_count: int,
    *,
    router_certainty: float = 0.9,
    calculation_certainty: float = 0.0,
    conflict_count: int = 0,
    ambiguity: bool = False,
) -> float:
    """Evidence-based score; the model never supplies its own confidence value."""
    return confidence_components(
        evidence, citation_count, router_certainty=router_certainty,
        calculation_certainty=calculation_certainty,
        conflict_count=conflict_count, ambiguity=ambiguity,
    )["score"]


def confidence_components(
    evidence: list[dict], citation_count: int, *, router_certainty: float = 0.9,
    calculation_certainty: float = 0.0, conflict_count: int = 0,
    ambiguity: bool = False,
) -> dict[str, float | int]:
    """Return safe, auditable confidence inputs (no report text)."""
    if not evidence:
        return {"score": 0.0, "relevance": 0.0, "support": 0.0,
                "citation_coverage": 0.0, "router_certainty": router_certainty,
                "calculation_certainty": calculation_certainty,
                "conflict_penalty": 0.0, "ambiguity_penalty": 0.0}
    # Qdrant cosine scores span [-1, 1]; normalize the strongest supporting passage.
    relevance = (max(float(item.get("score", 0.0)) for item in evidence) + 1.0) / 2.0
    # Multiple reports are not required to support a question about one report.
    # Use independent report pages instead of report-count diversity so a
    # single well-supported source is not assigned an artificial penalty.
    supporting_pages = {
        (item.get("report_id"), item.get("page"))
        for item in evidence
        if item.get("report_id") is not None
    }
    support = min(1.0, len(supporting_pages) / 2.0)
    citation_coverage = min(1.0, citation_count / max(1, len(evidence)))
    calculation = calculation_certainty
    conflict_penalty = 0.04 * min(conflict_count, 2)
    ambiguity_penalty = 0.04 if ambiguity else 0.0
    score = (
        0.40 * relevance
        + 0.20 * support
        + 0.25 * citation_coverage
        + 0.10 * router_certainty
        + 0.05 * calculation
        - conflict_penalty
        - ambiguity_penalty
    )
    return {"score": round(max(0.0, min(1.0, score)), 2),
            "relevance": round(relevance, 4), "support": round(support, 4),
            "citation_coverage": round(citation_coverage, 4),
            "router_certainty": router_certainty,
            "calculation_certainty": calculation_certainty,
            "conflict_penalty": conflict_penalty,
            "ambiguity_penalty": ambiguity_penalty}
