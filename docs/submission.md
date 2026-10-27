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

GitHub PR: https://github.com/Sumanthh381/Multi-MCP-Enterprise-Operations/pull/1 . The implementation was pushed successfully to `feat/enterprise-operations-copilot`, and PR #1 targets `main`. Initial REST API access returned Forbidden, but the authenticated GitHub CLI PR creation succeeded; no further credentials are required for this publication. Repository visibility and evaluator access were not changed. Remote CI status must be checked separately.
