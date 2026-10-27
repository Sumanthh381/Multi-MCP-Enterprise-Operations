"""Authenticated Alarm Management reference API. No generated code is ever executed."""

import hashlib
import hmac
import itertools
import json
import logging
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from enterprise.config import API_TOKEN
from enterprise.models import (
    AlarmRequest,
    CorrelationRequest,
    ExecuteRequest,
    Filters,
    FloodRequest,
    GenerateRequest,
    RationalizationRequest,
    RecommendationRequest,
    SummaryRequest,
    TrendsRequest,
)
from enterprise.seed import ALARMS, ASSETS, NOW

app = FastAPI(title="Alarm Management Simulator", version="1.0.0")
log = logging.getLogger("alarm-api")
security = HTTPBearer(auto_error=False)
CALCULATIONS: dict[str, GenerateRequest] = {}


def authorize(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials or not hmac.compare_digest(credentials.credentials, API_TOKEN):
        raise HTTPException(401, "Invalid bearer token")


@app.middleware("http")
async def metadata(request: Request, call_next):
    started = time.monotonic()
    trace = request.headers.get("trace_id", str(uuid4()))[:128]
    response = await call_next(request)
    response.headers["trace_id"] = trace
    for name in ("x-client-id", "x-metadata-tag"):
        if request.headers.get(name):
            response.headers[name] = request.headers[name][:128]
    log.info(
        json.dumps(
            {
                "trace_id": trace,
                "path": request.url.path,
                "api_status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        )
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok", "synthetic": True, "reference_time": NOW.isoformat()}


def filtered(f: Filters):
    return [
        a
        for a in ALARMS
        if (not f.asset_ids or a["asset_id"] in f.asset_ids)
        and (not f.site or a["site"] == f.site)
        and (not f.unit or a["unit"] == f.unit)
        and (not f.severity or a["severity"] in f.severity)
        and (not f.alarm_types or a["alarm_type"] in f.alarm_types)
        and (
            not f.time_range
            or f.time_range.start_time
            <= datetime.fromisoformat(a["start_time"])
            <= f.time_range.end_time
        )
    ]


def find_alarm(alarm_id):
    alarm = next((a for a in ALARMS if a["alarm_id"] == alarm_id), None)
    if not alarm:
        raise HTTPException(404, "Alarm not found")
    return alarm


def metrics(rows):
    counts = Counter((a["asset_id"], a["alarm_name"]) for a in rows)
    return {
        "alarm_count": len(rows),
        "critical_count": sum(a["severity"] == "critical" for a in rows),
        "recurring_rate": sum(n for n in counts.values() if n > 1) / max(1, len(rows)),
        "avg_ack_delay": statistics.mean(a["ack_delay_seconds"] for a in rows) if rows else 0,
        "suppression_candidate_rate": sum(n for n in counts.values() if n >= 5) / max(1, len(rows)),
    }


@app.get("/assets/search", dependencies=[Depends(authorize)])
def search(
    query: str = Query(min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=100),
    unit: str | None = None,
):
    return {
        "results": [
            a
            for a in ASSETS
            if (query.lower() in a["asset_name"].lower() or query.lower() in a["asset_id"].lower())
            and (not unit or a["unit"] == unit)
        ][:limit]
    }


@app.get("/assets/{asset_id}/metadata", dependencies=[Depends(authorize)])
def asset_metadata(asset_id: str):
    asset = next((a for a in ASSETS if a["asset_id"] == asset_id), None)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return {**asset, "manufacturer": "Synthetic Industries", "service": "Demonstration only"}


@app.get("/alarms", dependencies=[Depends(authorize)])
def alarms(
    asset_id: str | None = None,
    unit: str | None = None,
    site: str | None = None,
    status: Literal["active", "cleared"] | None = None,
    severity: Literal["low", "medium", "high", "critical"] | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: Literal["start_time", "severity", "alarm_id"] = "start_time",
    sort_order: Literal["asc", "desc"] = "desc",
):
    if (start_time and not start_time.tzinfo) or (end_time and not end_time.tzinfo):
        raise HTTPException(422, "Use timezone-aware timestamps")
    if start_time and end_time and start_time >= end_time:
        raise HTTPException(422, "Invalid time range")
    rows = filtered(
        Filters(
            asset_ids=[asset_id] if asset_id else [],
            unit=unit,
            site=site,
            severity=[severity] if severity else [],
        )
    )
    rows = [
        a
        for a in rows
        if (not status or a["status"] == status)
        and (not start_time or datetime.fromisoformat(a["start_time"]) >= start_time)
        and (not end_time or datetime.fromisoformat(a["start_time"]) <= end_time)
    ]
    rows.sort(key=lambda a: a[sort_by], reverse=sort_order == "desc")
    return {
        "data": rows[(page - 1) * page_size : page * page_size],
        "total": len(rows),
        "page": page,
        "page_size": page_size,
        "total_pages": (len(rows) + page_size - 1) // page_size,
    }


@app.post("/alarms/summary", dependencies=[Depends(authorize)])
def summary(body: SummaryRequest):
    rows = filtered(body)
    groups = defaultdict(list)
    for a in rows:
        groups[tuple(a[k] for k in body.group_by)].append(a)
    return {
        "totals": {k: v for k, v in metrics(rows).items() if k in body.kpis},
        "groups": [
            {
                **dict(zip(body.group_by, key)),
                **{k: v for k, v in metrics(values).items() if k in body.kpis},
            }
            for key, values in groups.items()
        ],
    }


@app.post("/alarms/trends", dependencies=[Depends(authorize)])
def trends(body: TrendsRequest):
    groups = defaultdict(list)
    for a in filtered(body):
        dt = datetime.fromisoformat(a["start_time"])
        if body.bucket == "weekly":
            dt -= timedelta(days=dt.weekday())
        key = dt.strftime("%Y-%m-%dT%H:00:00Z" if body.bucket == "hourly" else "%Y-%m-%d")
        groups[key].append(a)
    return {
        "bucket": body.bucket,
        "data": [
            {"start": k, **{m: metrics(v)[m] for m in body.metrics}}
            for k, v in sorted(groups.items())
        ],
    }


@app.post("/alarms/correlation", dependencies=[Depends(authorize)])
def correlation(body: CorrelationRequest):
    ranks = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    rows = [a for a in filtered(body) if ranks[a["severity"]] >= ranks[body.severity_threshold]]
    pairs: Counter = Counter()
    for a, b in itertools.combinations(rows, 2):
        left, right = (a["asset_id"], a["alarm_name"]), (b["asset_id"], b["alarm_name"])
        if (
            left != right
            and abs(
                (
                    datetime.fromisoformat(a["start_time"])
                    - datetime.fromisoformat(b["start_time"])
                ).total_seconds()
            )
            <= body.lag_window_minutes * 60
        ):
            pairs[tuple(sorted((left, right)))] += 1
    return {
        "method": body.correlation_method,
        "causality_proven": False,
        "pairs": [
            {
                "left": {"asset_id": a[0], "alarm_name": a[1]},
                "right": {"asset_id": b[0], "alarm_name": b[1]},
                "support": n,
            }
            for (a, b), n in pairs.items()
            if n >= body.min_support
        ],
    }


@app.post("/alarms/flood-analysis", dependencies=[Depends(authorize)])
def flood(body: FloodRequest):
    times = sorted(datetime.fromisoformat(a["start_time"]) for a in filtered(body))
    windows: list[dict] = []
    for start in times:
        end = start + timedelta(minutes=body.rolling_window_minutes)
        count = sum(start <= t < end for t in times)
        if count >= body.threshold_count and (
            not windows or start >= datetime.fromisoformat(windows[-1]["end"])
        ):
            windows.append(
                {"start": start.isoformat(), "end": end.isoformat(), "alarm_count": count}
            )
    return {"flood_windows": windows, "threshold_count": body.threshold_count}


@app.post("/alarms/rationalization-candidates", dependencies=[Depends(authorize)])
def rationalization(body: RationalizationRequest):
    groups = defaultdict(list)
    for a in filtered(body):
        groups[(a["asset_id"], a["alarm_name"])].append(a)
    return {
        "candidates": [
            {
                "asset_id": key[0],
                "alarm_name": key[1],
                "count": len(rows),
                "stale": any(a["duration_minutes"] >= body.stale_minutes_threshold for a in rows),
                "requires_engineering_review": True,
            }
            for key, rows in groups.items()
            if len(rows) >= body.recurrence_threshold
            or any(a["duration_minutes"] >= body.stale_minutes_threshold for a in rows)
        ]
    }


@app.post("/alarms/priority-score", dependencies=[Depends(authorize)])
def priority(body: AlarmRequest):
    a = find_alarm(body.alarm_id)
    severity = {"low": 1, "medium": 2, "high": 3, "critical": 4}[a["severity"]]
    return {
        "alarm_id": a["alarm_id"],
        "score": min(100, severity * 15 + a["criticality"] * 8),
        "formula": "min(100, severity_rank*15 + asset_criticality*8)",
    }


@app.post("/recommendations/operator-actions", dependencies=[Depends(authorize)])
def recommendations(body: RecommendationRequest):
    a = find_alarm(body.alarm_id)
    out = {
        "alarm_id": a["alarm_id"],
        "actions": [
            "Verify instrument readings and suction pressure",
            "Inspect lubrication and bearing vibration under approved procedure",
            "Escalate critical conditions to the shift supervisor; do not bypass trips",
        ],
    }
    if body.include_related:
        out["related"] = [
            r["alarm_id"]
            for r in ALARMS
            if r["asset_id"] == a["asset_id"] and r["alarm_id"] != a["alarm_id"]
        ][:5]
    if body.include_asset_context:
        out["asset"] = asset_metadata(a["asset_id"])
    if body.include_historical_pattern:
        out["recurrences"] = sum(
            r["asset_id"] == a["asset_id"] and r["alarm_name"] == a["alarm_name"] for r in ALARMS
        )
    return out


@app.post("/calculation-code/generate", dependencies=[Depends(authorize)])
def generate(body: GenerateRequest):
    key = hashlib.sha256(body.model_dump_json().encode()).hexdigest()[:24]
    CALCULATIONS[key] = body
    return {
        "calculation_id": key,
        "calculation_type": body.calculation_type,
        "execution": "allowlisted formula, never arbitrary code",
    }


@app.post("/calculation-code/execute", dependencies=[Depends(authorize)])
def execute(body: ExecuteRequest):
    definition = CALCULATIONS.get(body.calculation_id)
    if not definition:
        raise HTTPException(404, "Calculation not found; generate it first")
    f = body.filters.model_dump(exclude_none=True) or definition.filters.model_dump(
        exclude_none=True
    )
    start, end = f.pop("start_time", None), f.pop("end_time", None)
    if start and end:
        f["time_range"] = {"start_time": start, "end_time": end}
    rows = filtered(Filters(**f))
    m = metrics(rows)
    values = {
        "alarm_flood_index": len(flood(FloodRequest(**f))["flood_windows"]),
        "critical_alarm_density": m["critical_count"] / max(1, len(rows)),
        "operator_response_efficiency": sum(a["ack_delay_seconds"] <= 120 for a in rows)
        / max(1, len(rows)),
        "nuisance_alarm_score": m["recurring_rate"],
    }
    return {
        "calculation_id": body.calculation_id,
        "calculation_type": definition.calculation_type,
        "value": values[definition.calculation_type] if rows else None,
        "sample_count": len(rows),
        "unit": "ratio" if definition.calculation_type != "alarm_flood_index" else "windows",
    }


@app.get("/analytics/kpi-definitions", dependencies=[Depends(authorize)])
def definitions():
    return {
        "definitions": [
            {
                "name": "alarm_flood_index",
                "formula": "count of non-overlapping windows with >=10 alarms in 10 minutes",
            },
            {"name": "critical_alarm_density", "formula": "critical count / alarm count"},
            {
                "name": "operator_response_efficiency",
                "formula": "acknowledged within 120 seconds / alarm count",
            },
            {
                "name": "nuisance_alarm_score",
                "formula": "events in repeated asset/alarm groups / alarm count",
            },
        ]
    }


@app.get("/alarms/{alarm_id}", dependencies=[Depends(authorize)])
def alarm_detail(alarm_id: str):
    return find_alarm(alarm_id)
