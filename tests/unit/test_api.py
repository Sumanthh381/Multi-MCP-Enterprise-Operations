from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from enterprise.seed import NOW
from enterprise.simulator import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-token"}
PERIOD = {"start_time": (NOW - timedelta(days=90)).isoformat(), "end_time": NOW.isoformat()}


def test_auth_and_trace_metadata():
    assert client.get("/assets/search?query=pump").status_code == 401
    r = client.get(
        "/assets/search?query=pump",
        headers={**AUTH, "trace_id": "test-trace", "x-client-id": "test", "x-metadata-tag": "safe"},
    )
    assert len(r.json()["results"]) == 2
    assert r.headers["trace_id"] == "test-trace"
    assert r.headers["x-client-id"] == "test"
    assert r.headers["x-metadata-tag"] == "safe"


def test_pagination_sort_filters_and_detail():
    r = client.get("/alarms", params={"asset_id": "BFP-101", "page_size": 2}, headers=AUTH).json()
    assert len(r["data"]) == 2 and r["total"] >= 24 and r["total_pages"] >= 12
    assert r["data"][0]["start_time"] >= r["data"][1]["start_time"]
    assert client.get("/alarms/" + r["data"][0]["alarm_id"], headers=AUTH).json() == r["data"][0]
    assert (
        client.get(
            "/alarms", params={"severity": "critical", "status": "active"}, headers=AUTH
        ).json()["data"][0]["severity"]
        == "critical"
    )
    assert client.get("/alarms", params={"page": 0}, headers=AUTH).status_code == 422
    assert (
        client.get(
            "/alarms", params={"start_time": "2026-07-01", "end_time": "2026-01-01"}, headers=AUTH
        ).status_code
        == 422
    )
    assert client.get("/alarms/missing", headers=AUTH).status_code == 404
    assert client.get("/assets/missing/metadata", headers=AUTH).status_code == 404


def test_summary_filter_values_are_computed():
    filters = {
        "asset_ids": ["BFP-101"],
        "time_range": PERIOD,
        "severity": ["high", "critical"],
        "group_by": ["severity"],
        "kpis": ["alarm_count", "recurring_rate", "avg_ack_delay"],
    }
    r = client.post("/alarms/summary", json=filters, headers=AUTH)
    assert r.status_code == 200
    b = r.json()
    assert b["totals"]["alarm_count"] == sum(g["alarm_count"] for g in b["groups"])
    assert b["totals"]["recurring_rate"] == 1
    assert {g["severity"] for g in b["groups"]} == {"high", "critical"}
    filters["time_range"] = {
        "start_time": "2000-01-01T00:00:00Z",
        "end_time": "2000-02-01T00:00:00Z",
    }
    assert (
        client.post("/alarms/summary", json=filters, headers=AUTH).json()["totals"]["alarm_count"]
        == 0
    )


@pytest.mark.parametrize(
    "endpoint,extra,key",
    [
        ("trends", {"bucket": "hourly"}, "data"),
        ("correlation", {"min_support": 2}, "pairs"),
        ("flood-analysis", {"threshold_count": 10}, "flood_windows"),
        ("rationalization-candidates", {"recurrence_threshold": 5}, "candidates"),
    ],
)
def test_advanced_computed_results(endpoint, extra, key):
    b = {"asset_ids": ["BFP-101"], "time_range": PERIOD, **extra}
    r = client.post("/alarms/" + endpoint, json=b, headers=AUTH)
    assert r.status_code == 200
    assert len(r.json()[key]) > 0


@pytest.mark.parametrize(
    "kind",
    [
        "alarm_flood_index",
        "critical_alarm_density",
        "operator_response_efficiency",
        "nuisance_alarm_score",
    ],
)
def test_safe_calculation_chaining(kind):
    filters = {"site": "SouthPlant", **PERIOD}
    generated = client.post(
        "/calculation-code/generate",
        json={"calculation_type": kind, "filters": filters},
        headers=AUTH,
    ).json()
    result = client.post(
        "/calculation-code/execute",
        json={"calculation_id": generated["calculation_id"], "filters": filters},
        headers=AUTH,
    )
    assert result.status_code == 200 and result.json()["sample_count"] > 0
    assert result.json()["value"] >= 0


def test_invalid_calculations_and_requests():
    assert (
        client.post(
            "/calculation-code/generate",
            json={"calculation_type": "__import__('os')"},
            headers=AUTH,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/calculation-code/execute", json={"calculation_id": "missing"}, headers=AUTH
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/alarms/correlation", json={"lag_window_minutes": -1}, headers=AUTH
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/alarms/summary",
            json={
                "time_range": {
                    "start_time": "2026-07-01T00:00:00Z",
                    "end_time": "2026-01-01T00:00:00Z",
                }
            },
            headers=AUTH,
        ).status_code
        == 422
    )
    assert len(client.get("/analytics/kpi-definitions", headers=AUTH).json()["definitions"]) == 4


def test_priority_recommendation_context():
    row = client.get("/alarms?asset_id=BFP-101", headers=AUTH).json()["data"][0]
    body = {"alarm_id": row["alarm_id"]}
    assert 0 < client.post("/alarms/priority-score", json=body, headers=AUTH).json()["score"] <= 100
    out = client.post(
        "/recommendations/operator-actions",
        json={
            **body,
            "include_related": True,
            "include_asset_context": True,
            "include_historical_pattern": True,
        },
        headers=AUTH,
    ).json()
    assert out["related"] and out["recurrences"] > 0 and out["asset"]["asset_id"] == "BFP-101"
