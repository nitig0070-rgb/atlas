# Evaluation report

## Current run status

**Not run in this workspace.** Docker, PHP, and the AI service dependencies are not installed/available in the inspected environment. No accuracy score or successful live result is claimed. The runnable harness is `ai-service/evaluation/runner.py` and the 25 cases are in `ai-service/evaluation/questions.json`.

The available Python interpreter compiled the application, tests, and harness with `compileall`. The evaluation JSON parsed and contains 25 unique IDs. `python -m pytest ai-service/tests -q` could not start because `pytest` is not installed (`No module named pytest`).

## Metrics

The harness records HTTP success, safety-denial checks, citation overlap against expected reports, model confidence, escalation, and request latency. It does not yet calculate human-judged factual correctness, full citation entailment, cost, or token usage. Those metrics must not be inferred from citation overlap.

## Known expected failure modes to inspect in the first live run

1. **Vector corpus not ingested:** Qdrant starts empty until the documented `/ingest` commands run; retrieval will abstain.
2. **No LLM key/service:** generic fact lookup will escalate rather than produce generated prose.
3. **Embedding download/network failure:** ingestion and retrieval will fail safely; no fake retrieval fallback is enabled.
4. **Narrow numeric critic:** valid paraphrased number formatting may trigger a false escalation; unsupported numerical claims should be rejected.
5. **Router coverage:** current deterministic route phrases do not cover every natural-language variation, so aggregate or out-of-scope requests may route incorrectly.

After a live run, append measured category results and actual failing case IDs here. Do not replace this status with fabricated values.
