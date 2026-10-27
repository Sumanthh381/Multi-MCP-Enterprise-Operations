"""Deterministic intent planner and evidence composer; no hidden LLM dependencies."""

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from enterprise.registry import ToolFailure

INTENTS = {
    "efficiency": ("efficiency", "response time", "acknowledg"),
    "priority": ("highest", "priority", "escalat"),
    "flood": ("flood",),
    "trend": ("trend",),
    "rationalization": ("rationaliz", "stale", "nuisance"),
    "correlation": ("correlat", "contribut", "recurr", "investigat"),
}


def plan(message):
    lower = message.lower()
    return next(
        (name for name, words in INTENTS.items() if any(w in lower for w in words)), "summary"
    )


def asset_query(message, previous=None):
    match = re.search(
        r"(?:boiler\s+feed\s+pump|compressor|motor|control\s+valve)\s+\d+|(?:BFP|CMP|MOT|VAL)-\d+",
        message,
        re.IGNORECASE,
    )
    if match:
        return match.group(0)
    generic = re.search(r"\b(pump|compressor|motor|valve)\b", message, re.IGNORECASE)
    return generic.group(0) if generic else previous


class Copilot:
    def __init__(self, registry, retrieval):
        self.registry = registry
        self.retrieval = retrieval
        self.context = {}  # bounded, process-local demo sessions
        self.pending = {}

    async def run(self, message, conversation_id=None, degraded=False):
        conversation = conversation_id or str(uuid4())
        trace = str(uuid4())
        timeline: list[dict] = []
        warnings: list[str] = []
        intent = plan(message)
        response = {
            "conversation_id": conversation,
            "trace_id": trace,
            "intent": intent,
            "timeline": timeline,
            "sources": [],
            "warnings": warnings,
            "status": "complete",
            "facts": {},
            "actions": [],
        }
        query = asset_query(message, self.context.get(conversation))
        if not query:
            response.update(
                status="needs_input",
                answer="Which asset should I investigate? Include a name such as Boiler Feed Pump 101.",
            )
            return response

        async def call(name, args, optional=False):
            try:
                return await self.registry.call(name, args, trace, timeline)
            except ToolFailure as exc:
                if not optional:
                    raise
                warnings.append(str(exc))
                return None

        try:
            assets = await call("alarm.search_assets", {"query": query})
            if not assets["results"]:
                response.update(
                    status="empty",
                    answer=f"No asset matched {query}. Check the name or identifier.",
                )
                return response
            if len(assets["results"]) > 1:
                response.update(
                    status="needs_input",
                    answer="Several assets match. Please specify one: "
                    + ", ".join(a["asset_name"] for a in assets["results"]),
                )
                return response
            asset = assets["results"][0]
            if len(self.context) >= 500:
                self.context.pop(next(iter(self.context)))
            self.context[conversation] = asset["asset_name"]
            metadata = await call("alarm.asset_metadata", {"asset_id": asset["asset_id"]})
            now = datetime.now(UTC)
            days_match = re.search(r"(?:last|past)\s+(\d+)\s+days?", message, re.IGNORECASE)
            days = min(3650, max(1, int(days_match.group(1)))) if days_match else 90
            explicit = re.search(
                r"(\d{4}-\d{2}-\d{2})\s+(?:to|through)\s+(\d{4}-\d{2}-\d{2})", message
            )
            period = {
                "start_time": (now - timedelta(days=days)).isoformat(),
                "end_time": now.isoformat(),
            }
            if explicit:
                period = {
                    "start_time": explicit.group(1) + "T00:00:00Z",
                    "end_time": explicit.group(2) + "T23:59:59Z",
                }
            filters = {"asset_ids": [asset["asset_id"]], "time_range": period}
            if any(w in message.lower() for w in ("high-severity", "high severity", "critical")):
                filters["severity"] = ["high", "critical"]
            summary = await call(
                "alarm.alarm_summary",
                {
                    "request": {
                        **filters,
                        "group_by": ["alarm_name", "severity"],
                        "kpis": ["alarm_count", "recurring_rate", "avg_ack_delay"],
                    }
                },
            )
            rows: list[dict] = []
            page = 1
            while True:
                data = await call(
                    "alarm.get_alarms",
                    {"asset_id": asset["asset_id"], **period, "page": page, "page_size": 50},
                )
                rows.extend(
                    a
                    for a in data["data"]
                    if not filters.get("severity") or a["severity"] in filters["severity"]
                )
                if page >= data["total_pages"]:
                    break
                page += 1
                if page > 100:
                    warnings.append("Alarm pagination capped at 100 pages; analysis is incomplete")
                    break
            facts = {
                "asset": metadata,
                "time_range": period,
                "summary": summary,
                "alarm_ids": [a["alarm_id"] for a in rows],
            }
            response["facts"] = facts
            operation = {
                "correlation": "correlate_alarms",
                "trend": "alarm_trends",
                "flood": "flood_analysis",
                "rationalization": "rationalization_candidates",
            }.get(intent)
            if operation:
                facts[intent] = await call(
                    f"alarm.{operation}", {"request": filters}, optional=True
                )
            if intent == "efficiency":
                calc_filters = {"site": asset["site"], **period}
                definition = await call(
                    "alarm.generate_calculation",
                    {
                        "request": {
                            "calculation_type": "operator_response_efficiency",
                            "filters": calc_filters,
                        }
                    },
                )
                facts["efficiency"] = await call(
                    "alarm.execute_calculation",
                    {
                        "request": {
                            "calculation_id": definition["calculation_id"],
                            "filters": calc_filters,
                        }
                    },
                )
            if rows:
                severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
                highest = max(rows, key=lambda a: (severity_rank[a["severity"]], a["criticality"]))
                facts["priority"] = await call(
                    "alarm.priority_score", {"request": {"alarm_id": highest["alarm_id"]}}
                )
                facts["recommendations"] = await call(
                    "alarm.operator_recommendations",
                    {"request": {"alarm_id": highest["alarm_id"], "include_related": True}},
                    optional=True,
                )
            history_tool = (
                "workorders.unavailable_demo" if degraded else "workorders.maintenance_history"
            )
            facts["maintenance"] = await call(
                history_tool, {"asset_id": asset["asset_id"]}, optional=True
            )
            doc_query = f"{message} {' '.join(g['alarm_name'] for g in summary['groups'])}"
            sources = self.retrieval.search(
                doc_query,
                asset_type="pump" if "pump" in asset["asset_name"].lower() else "rotating",
            )
            response["sources"] = sources
            if not sources:
                warnings.append(
                    "No sufficiently relevant operating procedure found; recommendations withheld"
                )
            observations = f"{asset['asset_name']}: {summary['totals']['alarm_count']} matching alarms from {period['start_time']} to {period['end_time']}."
            if facts.get("efficiency"):
                efficiency = facts["efficiency"]
                observations += f" Site response efficiency: {efficiency['value']} ({efficiency['sample_count']} events; fraction acknowledged within 120 seconds)."
            if not rows:
                observations += " No alarm events were found in this range; no recurring pattern can be inferred."
            if sources and rows:
                response["actions"] = [
                    {"text": s["text"], "citation": s["citation"]} for s in sources
                ]
                observations += (
                    " Use the cited procedure excerpts for verification steps; retrieved guidance does not establish a root cause. "
                    + " ".join(s["citation"] for s in sources)
                )
                if facts.get("maintenance") and facts["maintenance"]["records"]:
                    observations += (
                        " Synthetic maintenance finding: "
                        + facts["maintenance"]["records"][0]["finding"]
                        + " [maintenance:"
                        + facts["maintenance"]["records"][0]["work_order_id"]
                        + "]. Treat these as possible contributing factors requiring field verification."
                    )
            response["answer"] = observations
            if any(w in message.lower() for w in ("draft", "issue", "ticket", "escalat")):
                draft = await call(
                    "workorders.prepare_issue_draft",
                    {
                        "asset_id": asset["asset_id"],
                        "title": f"Investigate {asset['asset_name']}",
                        "evidence": observations,
                    },
                    optional=True,
                )
                if draft:
                    self.pending[draft["draft_id"]] = conversation
                    response["draft"] = draft
            response["status"] = "partial" if warnings else ("empty" if not rows else "complete")
        except ToolFailure as exc:
            response.update(status="failed", answer="Investigation could not complete: " + str(exc))
        return response

    async def confirm(self, draft_id, conversation, confirmed):
        if not confirmed or self.pending.get(draft_id) != conversation:
            raise ToolFailure("Confirmation requires a draft from this conversation")
        timeline: list[dict] = []
        result = await self.registry.call(
            "workorders.create_ticket",
            {"draft_id": draft_id, "confirmed": True},
            str(uuid4()),
            timeline,
        )
        return {"ticket": result, "timeline": timeline}
