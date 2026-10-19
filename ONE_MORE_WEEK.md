# What I Would Do With One More Week
**Candidate:** AI Software Developer (Generative & Agentic AI)  
**Project:** Project Atlas — Market Research Copilot

---

## 1. Engineering Philosophy: What Was Prioritized vs. What Was Cut

In commercial market research, **a wrong number delivered to an enterprise client is vastly worse than no answer.** Therefore, the engineering priority for Project Atlas was absolute correctness, zero data leakage, and verified citation grounding:

1. **Prioritized**:
   - Pre-retrieval and post-retrieval multi-tenant entitlement boundary enforcement.
   - Deterministic calculation engines for CAGR and derived estimates to eliminate arithmetic hallucinations.
   - Fail-closed security architecture for prompt-injection defense and SQL execution.
   - Explicit confidence scoring and automatic ticket escalation when evidence is insufficient.
2. **Deliberately Cut & Deferred**:
   - **Cross-Client Semantic Caching**: A naive shared vector cache risks severe cross-tenant data leakage (e.g., Client C-02 inadvertently receiving cached answer chunks generated for C-01's premium reports). Caching was deferred until tenant-partitioned invalidation could be architected.
   - **Dynamic Text-to-SQL**: Exposing open-ended LLM-generated SQL against enterprise databases introduces prompt-injection vulnerabilities and query timeout denial-of-service. We restricted aggregates to fixed, parameterized read-only queries.
   - **Complex Chart/Image Parsing**: Ingested reports as structured Markdown with exact page headers rather than adding heavyweight PDF OCR libraries to maintain sub-10-minute Docker reproducibility.

---

## 2. The 7-Day Production Roadmap

If granted one additional week, I would execute the following 5 engineering initiatives to transition Project Atlas from a high-performing prototype into an enterprise-grade production platform:

### Day 1–2: Hybrid Retrieval & Cross-Encoder Re-Ranking (RAG Excellence)
- **Sparse + Dense Hybrid Search**: Combine Qdrant dense vector embeddings (`all-MiniLM-L6-v2`) with sparse lexical BM25 search via Reciprocal Rank Fusion (RRF). This ensures exact keyword matching for precise industry acronyms (e.g., `AMR / AMI`, `CAGR`, `RO/UV`) alongside semantic thematic search.
- **Cross-Encoder Re-Ranker**: Deploy a lightweight local re-ranking model (`BAAI/bge-reranker-base`) as a LangGraph node to re-score candidate passages, elevating true evidence to the top 3 context slots and lifting citation overlap above 95%.
- **Agentic Query Decomposition**: For multi-part queries (e.g., *"Compare APAC growth across water meters and EV charging"*), implement a LangGraph sub-graph that breaks questions into parallel atomic retrieval tasks before synthesis.

### Day 3: Cryptographically Partitioned Semantic Caching
- **Tenant-Safe Cache Architecture**: Implement an in-memory Redis semantic cache with composite keys:
  $$\text{Cache Key} = \text{HMAC-SHA256}(\text{Normalized Query},\; \text{Client ID} \parallel \text{Entitlement Hash})$$
- **Cache Invalidation Lifecycle**: Invalidate tenant cache entries automatically whenever a client purchases a new report or when report metadata updates.
- **Latency Impact**: Drop median repeat-query latency from ~2,300 ms down to under 80 ms while guaranteeing zero cross-tenant leakage.

### Day 4: Multimodal Ingestion of Charts, Tables & Coordinate Citations
- **Visual Data Extraction**: Build an asynchronous ingestion pipeline using a Vision LLM to parse infographics, bar charts, and tabular matrices from source PDFs into structured JSON and Markdown tables.
- **Bounding-Box Citations**: Store source coordinate metadata `[x1, y1, x2, y2, page_number]` in Qdrant payloads, enabling the CodeIgniter 3 UI to render interactive PDF preview snippets highlighting the exact cited source table.

### Day 5: Enterprise Observability & Token Economics
- **Distributed Tracing with Langfuse / OpenTelemetry**: Instrument every LangGraph node (Router, Retriever, Critic, Writer) with OpenTelemetry spans to capture exact prompt/completion latencies, model token counts, and token cost in USD.
- **Budgeting & Rate Limiting**: Implement per-tenant token quotas, sliding-window rate limiters, and automated alerting for anomalous query patterns or repeated injection attempts.

### Day 6: Human-in-the-Loop Analyst Workbench in CodeIgniter 3
- **Escalation Review Portal**: Expand the CI3 application with an authenticated `/analyst` dashboard displaying open tickets from the `escalations` table.
- **Feedback Loop**: Allow human senior analysts to inspect low-confidence queries, edit draft responses, approve citations, and dispatch answers directly to clients.
- **Continuous Alignment**: Store verified analyst corrections in MySQL to automatically curate an expanding Golden Evaluation Dataset for ongoing model regression testing.

### Day 7: Automated Red-Teaming & Production Hardening
- **Adversarial Evaluation Suite**: Build an automated red-teaming pipeline using Garak / PyRIT to subject the API to multi-turn jailbreaks, indirect prompt injections, base64 obfuscation, and data exfiltration vectors.
- **Infrastructure as Code**: Provide a Terraform script for single-command deployment to AWS ECS Fargate or a hardened Linux VPS with automated SSL and daily database backups.

---

## 3. Summary
Project Atlas proves that a compact, rigorously validated system built around **entitlement awareness, deterministic grounding, and safe escalation** delivers superior enterprise reliability. With one more week, the platform would achieve sub-100ms cached speeds, multimodal extraction, and full operational observability.
