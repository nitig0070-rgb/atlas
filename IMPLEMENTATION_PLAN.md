# Project Atlas Implementation Plan

## Repository inspection

The target workspace was empty at inspection time; there is no existing CI3 application, Python service, schema, tests, or repository guidance to preserve. The pasted implementation brief and the attached five-page assignment PDF were both reviewed before application code is written.

## Requirement reconciliation

The PDF describes a focused 2-3 day build, accepts scope cuts, and awards safety/correctness over breadth. The pasted brief supplies a much larger detailed checklist. The implementation will preserve the PDF's core constraints and use the pasted checklist to guide depth. Where report-count requirements differ, meet the stricter interpretation: three mandatory seed reports plus at least four additional fictional reports (seven total). Preserve all exact seed figures and the R-102 page-14 injection trap. The PDF sample set of ten questions is mandatory; the pasted brief requires at least 25, so the eventual evaluation set will include at least 25.

The assignment's 72-hour submission and video instructions are operational deliverables for the candidate. This work can prepare the repository and a demo script, but sharing with a recruiter and recording/submitting a video remain manual actions.

Access-seed reconciliation: the PDF says C-01's purchases are R-101 and R-103, but its first sample question requires C-01 to show R-102's figure; the PDF also labels R-102 a public excerpt and says C-02 must not receive it. The seed models C-01's R-102 access as an explicit excerpt grant, not a purchase. C-02 has no R-102 entitlement. This is necessary to meet both behaviors.

## Architecture decision summary

Use FastAPI + typed Pydantic schemas, LangGraph for visible state transitions, SQLAlchemy/MySQL for authoritative relational data, Qdrant for vector retrieval, real embeddings, a provider adapter for Groq/OpenAI/Gemini/Ollama, and CI3/PHP as a server-side client. Enforce report allow-lists before vector search and again before LLM context construction. Keep calculations and SQL query selection deterministic. Persist conversations, feedback, escalations, request metrics, and sanitized security events in MySQL. Run services in Docker Compose.

## Phases and completion gates

Each phase is implemented and verified before the next phase. No test/evaluation result will be claimed unless the command actually ran.

1. **Architecture (current):** document trust boundaries, choices, request flow, graph, and invariant. Gate: architecture and plan exist before application files.
2. **Project skeleton/config:** create modular AI service, PHP integration scaffold, SQL init, Compose, `.env.example`, and secret-safe ignore rules. Gate: static structure and Compose configuration parse.
3. **Relational schema/seed:** constraints, foreign keys, normalized entitlement grants, exact assignment seed rows. Gate: seed SQL reviewed against source values; database startup check where Docker is available.
4. **Synthetic corpus:** seven or more complete Markdown reports with page/section metadata; exact R-101 p.8 and R-102 p.14 trap. Gate: automated corpus integrity check.
5. **Ingestion/vector store:** parser, deterministic chunk IDs, metadata, real embeddings, idempotent upsert, protected `/ingest`. Gate: ingest and retrieve from a running vector store when available.
6. **Entitlement retrieval/security:** retrieve only after normalized entitlement lookup; post-filter assertions, injection flagging, safe logging. Gate: cross-client boundary tests prove unauthorized text never reaches model boundary.
7. **API/agent tools:** typed endpoints and errors; LangGraph routes; deterministic calculator; allow-listed read-only aggregate SQL. Gate: focused API/unit tests.
8. **Evidence/critic/confidence/escalation:** citations, source conflict, derived labeling and formulas, confidence, MySQL escalation. Gate: tests cover the ten assignment questions and numerical validation.
9. **CI3 integration:** controller, API library, session-derived client identity, CSRF, safe escaping, feedback and graceful timeout. Gate: PHP syntax checks and manual page flow where runtime is available.
10. **Compose/observability/cache:** health checks, service dependencies, persistence, structured logs, latency/cost records, entitlement-scoped deterministic cache if it does not compromise safety. Gate: compose config and startup smoke check.
11. **Evaluation and hardening:** at least 25 cases, report actual metrics and five or more failure analyses; red-team cases for injection, entitlement bypass, SQL writes, XSS, malformed/missing input, API key, long/repeated requests. Gate: run suite, fix failures, rerun.
12. **Docs and viva:** README, SECURITY, DEMO, ONE_MORE_WEEK, EVALUATION, VIVA, architecture updates, honest known limitations and exact commands. Gate: all instructions match implemented behavior.

## Risk controls and honest scope

- No mock answers, fake citations, or simulated successful database/vector calls. If Docker, dependencies, credentials, or provider access are unavailable in the environment, preserve the failing evidence and document what could not be exercised.
- External LLM credentials are intentionally not included. Without a configured provider, answer generation must fail safely or escalate; this cannot be represented as a successful end-to-end model test.
- Prefer a working, safe vertical slice over ornamental breadth. Any incomplete requirement will be listed with its impact and workaround rather than claimed complete.
- Do not invent commit history. Create commits only if the workspace is a Git repository and a real commit is appropriate.

## Deliverable status

- [x] Requirements reviewed from pasted brief and assignment PDF.
- [x] Workspace inspected; empty at start.
- [x] Architecture written before application implementation.
- [x] Phased implementation plan written before application implementation.
- [x] Initial application and infrastructure scaffold implemented.
- [ ] Full runtime integration verified (Docker/PHP/dependencies are unavailable locally).
- [ ] Automated tests and evaluation run (pytest is not installed in the available interpreter).
- [x] Architecture, security, demo, evaluation status, one-more-week, and viva documentation drafted.

## Current implementation notes

Implemented so far: typed FastAPI routes, configurable model adapter, LangGraph routing/retrieval/answer path, Qdrant with sentence-transformer embeddings and report-ID filtering, SQL-seeded metrics and entitlement joins, deterministic comparison/calculation paths, numeric-support guard, heuristic confidence scoring, escalation and conversation persistence/history, sanitized security events, request latency and provider-token logs (with configurable cost-rate estimates), CI3 controller/library/view, seven Markdown reports, 25 evaluation cases, Compose, and documentation. Static Python compilation and evaluation JSON integrity checks passed. No live API, MySQL, Qdrant, PHP, or Compose checks were possible here.

Known incomplete acceptance areas: no live evaluation results; no semantic cache; estimated cost stays null unless accurate model rates are configured; confidence is heuristic and uncalibrated; numeric critic is a conservative string-support check rather than semantic claim verification; API failure coverage is incomplete; CI3 client selection is demo-only; runtime stack has not been built or started. This is implementation in progress, not a verified submission.
