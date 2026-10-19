# Viva notes

1. **Why LangGraph?** The graph makes the route and guard/tool transitions inspectable; `ai-service/app/agent.py` uses typed state, router, retrieval and answer nodes.
2. **Why Qdrant?** It supports vector search with metadata filters, including the report-ID allow-list.
3. **Entitlements?** `database.entitled_reports` reads the normalized composite-key table before retrieval; the retriever filters then asserts again.
4. **Unauthorized text and LLM?** Qdrant receives only entitled report IDs; post-filter checks every result before it becomes evidence. The LLM writer only accepts that evidence list.
5. **Injection?** User exfiltration prompts are rejected before the graph; retrieved R-102 trap text is detected and logged, while writer instructions explicitly classify report text as untrusted data.
6. **SQL writes?** The model cannot supply SQL. Aggregate uses a fixed SELECT statement, while the reader role has SELECT only.
7. **Conflicts?** The comparison path presents R-101's broad scope and R-102's hardware-only scope side by side and never averages them.
8. **CAGR?** The deterministic calculator computes base × (1 + CAGR)^periods and shows inputs and formula.
9. **Trust derived values?** The calculation is deterministic and inputs are cited, but the base-period ambiguity is stated; it remains an estimate, not a quoted fact.
10. **Confidence?** Route-specific evidence confidence and ambiguity thresholds are explicit. This first version is heuristic, not calibrated on a labeled dataset.
11. **Escalation?** Missing evidence, provider failure, or low confidence creates a MySQL ticket.
12. **Citations?** Each retrieved passage includes report ID, title and page and is returned with a short quote.
13. **Hallucinations?** Evidence-only prompt, numeric check, and abstention reduce risk; semantic entailment is a known limitation.
14. **CI3 communication?** A PHP library makes server-side JSON POST to FastAPI with API key and timeouts.
15. **API failure?** The PHP library returns a fixed safe service-unavailable message; FastAPI returns structured errors without stack traces.
16. **XSS?** View output uses `html_escape`.
17. **CSRF?** CI3 CSRF is enabled and forms include its token.
18. **Docker startup?** Compose starts MySQL, Qdrant, FastAPI and Apache/PHP with health dependencies and named volumes.
19. **Evaluation?** The 25-case harness is provided, but no live score is claimed until run with services and credentials.
20. **One more week?** See `ONE_MORE_WEEK.md`: real identity, stronger evaluation, hybrid retrieval, cache, PDF extraction and operations hardening.
