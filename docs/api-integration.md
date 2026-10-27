# Alarm API integration

The original supplied Postman collections are preserved under `postman/`. They specify URLs, bearer authentication, request bodies, chaining variables and a few response fields; they do not contain complete example responses or exhaustive JSON schemas. The simulator supplies deterministic domain semantics and documents the remaining response structures in [OpenAPI](alarm-openapi.json). The live API exposes `/docs` and `/openapi.json`.

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/health` | Public readiness, synthetic flag and reference clock |
| GET | `/assets/search` | Case-insensitive name/ID search, limit and unit filter; `results` |
| GET | `/assets/{asset_id}/metadata` | Site, unit and criticality; missing IDs give 404 |
| GET | `/alarms` | Asset/site/unit/status/severity/time filters, sorting and pagination; `data`, `total`, `total_pages` |
| GET | `/alarms/{alarm_id}` | Event detail |
| POST | `/alarms/summary` | Filtered dimension groups and computed KPIs |
| POST | `/alarms/trends` | Hourly/daily/weekly event and acknowledgement buckets |
| POST | `/alarms/correlation` | Co-occurrence pairs within lag window and minimum support |
| POST | `/alarms/flood-analysis` | Thresholded rolling windows; `flood_windows[].start/end` |
| POST | `/alarms/rationalization-candidates` | Recurrent/stale groups, review required |
| POST | `/alarms/priority-score` | Severity rank and asset criticality formula |
| POST | `/recommendations/operator-actions` | Advisory actions and optional context |
| POST | `/calculation-code/generate` | Register allowlisted formula; `calculation_id` |
| POST | `/calculation-code/execute` | Evaluate registered formula and filter; no eval/exec |
| GET | `/analytics/kpi-definitions` | Four calculation definitions |

All operations except health require `Authorization: Bearer <ALARM_API_TOKEN>`. `demo-token` is the public fixture value supplied by the assignment, not a production secret. Production credentials belong in environment settings and must not be committed. API response headers echo `trace_id`, `x-client-id`, `x-metadata-tag` (bounded to 128 characters); the connector forwards all three.

Schemas reject unknown body properties and invalid enum/range/date values. Time ranges must be timezone-aware and ordered. GET pagination accepts pages >=1, page sizes 1–200. Grouping and sort fields are allowlisted. SQL uses bound parameters. Unknown assets/alarms/calculations return 404. Unauthenticated access returns 401. Invalid requests return 422. Source failures are mapped by the MCP connector with sanitized errors and bounded retries.

## Data and formulas

Nine assets cover every named Postman chain. Each has 24 historical events in June 2026 and 24 rolling events near runtime minus 30 days. The optional `SIMULATOR_NOW` setting pins the synthetic clock; default uses current UTC. The planner uses current UTC for natural-language ranges; use explicit ISO date ranges for historical fixture checks. Data is demonstrative, not a validated industrial alarm model. Priority: `min(100, severity_rank*15 + criticality*8)`. Response efficiency: fraction acknowledged within 120 seconds, not proof of resolution. All other formulas are discoverable through KPI definitions.

## Validation commands

Start the source: `.venv/bin/uvicorn enterprise.simulator:app --port 8000`.

```sh
npx newman run postman/Alarm-API-Simulator.postman_collection.json
npx newman run postman/scenarios/Alarm-API-Scenarios.postman_collection.json
npx newman run postman/chaining/Alarm-API-Chaining.postman_collection.json
```

All 62 requests returned HTTP 200 in the recorded run. The ten chaining flows passed their embedded assertions. The supplied chaining collection uses top-level `pm.expect` statements, so Newman's named-assertion counter is zero for that collection; this is distinct from zero requests. API unit tests additionally verify computed values, invalid inputs, missing resources, dates, authentication and trace propagation. Newman JSON evidence is stored in `docs/evidence`.
