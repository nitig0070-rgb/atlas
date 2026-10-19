# What I would do with one more week

1. Replace demo client switching with the portal's real identity/session integration and add per-client analyst permissions.
2. Expand the evaluation set with human-written expected claims, semantic citation entailment checks, and measured precision/recall by route.
3. Add a cross-client-safe semantic cache keyed by normalized question and an entitlement-set version, with explicit invalidation.
4. Add hybrid lexical/vector retrieval and a reranker, then benchmark citation quality against the current vector-only baseline.
5. Improve PDF/table/chart extraction and preserve source coordinates and page rendering for reviewer inspection.
6. Add distributed tracing, provider token/cost capture, dashboards, rate limits, and operational alerting.
7. Harden MySQL secrets and least-privilege grants, add production migrations/backups, and deploy through a reproducible Linux CI pipeline.
8. Red-team prompt injection and authorization boundaries continuously, including cache, logging, and exception paths.
