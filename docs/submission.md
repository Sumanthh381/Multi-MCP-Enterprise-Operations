# Submission notes

Repository: https://github.com/Sumanthh381/Multi-MCP-Enterprise-Operations

Implementation branch: `feat/enterprise-operations-copilot`.

Selected use case: Multi-MCP Enterprise Operations Copilot.

MCP servers: independently runnable Alarm Management (`python -m enterprise.alarm_mcp`) and Work Orders (`python -m enterprise.workorders_mcp`), with official SDK stdio clients and 17 discovered tools.

Document RAG: three synthetic Markdown documents; `make ingest`; paragraph-aware chunks, sparse TF-IDF/lexical hybrid retrieval, asset filters, verbatim citations and low-confidence handling.

Run: `docker compose up --build` or `make install && make ingest && make run`.

Tests: `make check && make test`; functional running-app check `python scripts/smoke.py`.

Demo: [short video](evidence/demo.mp4), [successful investigation](evidence/03-investigation.png), [degraded case](evidence/05-degraded.png).

Known limitations: [documented explicitly](known-limitations.md). This is a reproducible synthetic demonstration with bounded planning and local mock tickets, not an unrestricted LLM or industrial control system.

Implementation time: no candidate-provided estimate was supplied; no human working-hours claim is fabricated.

GitHub PR: API access from this environment returned Forbidden. Git transport push access was separately verified. A prepared PR description is in `docs/pull-request.md`; the branch comparison link is https://github.com/Sumanthh381/Multi-MCP-Enterprise-Operations/compare/main...feat/enterprise-operations-copilot?expand=1 . Do not interpret this comparison link as an already-created PR. Environment settings contain a draft addition for `api.github.com`; saving a draft does not establish live API access. Repository visibility and evaluator access were not changed.
