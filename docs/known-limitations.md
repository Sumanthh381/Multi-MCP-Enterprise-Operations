# Known limitations and future improvements

- Local demonstration, not a production-certified industrial control or safety system. All fixtures and documents are synthetic.
- The deterministic keyword planner supports documented intents and asset/time extraction. It is not a general-purpose LLM, does not infer arbitrary API plans, and does not yet support comparative multi-asset chat questions. MCP tools themselves accept multi-asset filters.
- Mock tickets are persisted locally, not sent to GitHub or an external enterprise service. GitHub publishing of this submission is separate from application ticket creation.
- Shared MCP output envelope is typed and validated, but operation-specific JSON `data` payloads are not all represented by strict Pydantic response models. Captured schemas, OpenAPI and examples document them.
- No multi-user identity, session authorization, rate limiting or distributed state. Conversation context is bounded in memory; pending drafts in the backend are not restored after restart, although SQLite records survive. Run on loopback or behind an authenticated gateway.
- Retrieval confidence is heuristic. Prompt-injection quarantine uses patterns; architectural isolation and extractive rendering supply the stronger boundary. PDF/OCR ingestion, multilingual retrieval, cross-encoders, automated conflict detection and large-corpus evaluations are future work.
- Correlation is co-occurrence, not causal inference. Sample priority and efficiency formulas are not plant-approved standards. Recommendations require operator review.
- API calculations are kept in memory and must be regenerated after simulator restart. Flood/correlation algorithms target small synthetic datasets; add indexed range queries and streaming windows for large deployments.
- Logs include safe operational metadata; there is no OpenTelemetry exporter or production log retention policy.
- The demo is a short silent browser recording. It covers success, discovery, citations, explicit approval and degraded operation; no human narration is claimed.
