# Assignment requirement checklist

This maps the supplied assignment to actual implementation and evidence, including limits. Original assignment documents are in [assignment](assignment/).

| Requirement | Implementation / evidence |
|---|---|
| Full reference API simulator before integration | `simulator.py`; original `postman/`; all 62 reference requests run by Newman |
| Authentication, trace headers, pagination, chaining | API unit tests, connector tests, real MCP integration, Newman JSON reports |
| Alarm MCP server | `alarm_mcp.py`, 14 real SDK tools; independently runnable |
| Additional MCP server | `workorders_mcp.py`, 3 tools; SQLite maintenance, draft and approved mock ticket |
| MCP discovery and schemas | `registry.py`; 17 tools; GUI registry; complete catalog and `tool-schemas.json` |
| MCP invocation, cross-server chaining | `orchestrator.py`; asset IDs drive both domains; generated KPI IDs feed execution |
| Validation and error mapping | JSON Schema + Pydantic; input/output envelope; sanitized API errors |
| Timeout, retry and partial failures | Connector retry tests; MCP deadline; degraded UI scenario; failure tests |
| Document corpus and ingestion | Three synthetic Markdown documents, extractor/chunker/metadata pipeline |
| Equivalent embeddings, vector/hybrid retrieval | TF-IDF sparse vectors + cosine + lexical score, asset filters |
| Citations and grounded generation | Exact excerpts with document ID, revision, paragraph and hash; GUI evidence panel |
| No-result and low-confidence retrieval | Retrieval tests and orchestration test; actions withheld |
| Prompt-injection protections | Quarantine patterns plus no document-to-tool control path; no LLM execution |
| Combined mandatory scenario | Real backend → MCP → simulator + work orders + RAG; automated E2E; screenshots/video |
| Natural language and context | Bounded intent planner, multiple assets and dates, follow-up asset retention; documented language limits |
| Chat GUI | Responsive frontend with loading, empty, error and partial states |
| Tool traceability and schema inspection | Server/tool, input/output, duration, status, retry count and trace IDs in GUI |
| Issue/ticket approval | Local draft then separate confirmed route; conversation ownership and idempotence tests |
| Unit/API client tests | `tests/unit` |
| MCP server/client integration tests | `tests/integration/test_mcp.py`, exercises every tool over actual stdio |
| RAG ingestion/retrieval tests | `tests/unit/test_rag.py` |
| Orchestration/error tests | Unit failure tests, real missing-evidence integration, E2E degraded scenario |
| Test evidence / coverage | JUnit and coverage JSON; see validation report for exact run |
| Architecture and diagram | `architecture.md`, PNG and editable SVG, explicitly includes both MCP and RAG |
| API documentation | `api-integration.md`, captured OpenAPI, original reference collections |
| Every MCP tool documented | Generated catalog: purpose, schemas, auth, timeout, errors, source operation, real examples |
| RAG design and index instructions | `rag-design.md`, `make ingest`, retrieval example JSON |
| Environment config | `.env.example`, exported variables, no real secrets committed |
| Dockerfile / Compose / health ordering | Non-root/read-only containers; real Compose functional validation |
| CI | GitHub Actions formatting/lint/static/tests/audit/build/smoke; remote result must be checked separately |
| Demo screenshots + video <=10 minutes | Six browser screenshots and short MP4 linked in README; successful and degraded workflows |
| Known limitations / future improvements | `known-limitations.md`, design decisions, README |
| Meaningful commits and PR | Feature branch, implementation/test/docs commits; PR creation depends on GitHub API access, see submission status |
| GitHub publication / evaluator access | Git push to supplied repository; visibility/access is inherited and not changed |
| TDD expectation | Automated tests present and executed; strict red/green commit history is not claimed |

No code-generated assessment score or claim of production certification is supplied. The limitations document explicitly identifies bounded language planning, mock rather than external ticket writes, flexible per-operation output payloads and missing production identity controls.
