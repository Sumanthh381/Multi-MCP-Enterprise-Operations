import httpx
import pytest


def ask(services, message, **kwargs):
    r = httpx.post(
        services["backend"] + "/api/chat", json={"message": message, **kwargs}, timeout=30
    )
    assert r.status_code == 200
    return r.json()


def test_acceptance_combines_real_mcp_api_rag_and_secondary_server(services):
    body = ask(
        services,
        "Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last 90 days and prepare an issue draft",
    )
    assert body["status"] == "complete"
    assert body["facts"]["summary"]["totals"]["alarm_count"] > 0
    assert body["sources"] and all(s["citation"] in body["answer"] for s in body["sources"])
    assert body["facts"]["maintenance"]["records"]
    keys = [e["tool"] for e in body["timeline"]]
    assert (
        keys.index("alarm.search_assets")
        < keys.index("alarm.get_alarms")
        < keys.index("workorders.maintenance_history")
    )
    assert any(k == "alarm.correlate_alarms" for k in keys)
    assert all(e["status"] == "success" for e in body["timeline"])
    assert {e["trace_id"] for e in body["timeline"]} == {body["trace_id"]}
    assert body["draft"]["status"] == "awaiting_confirmation"
    continuation = ask(services, "Show its trends", conversation_id=body["conversation_id"])
    assert continuation["facts"]["asset"]["asset_id"] == "BFP-101"
    payload = {"draft_id": body["draft"]["draft_id"], "conversation_id": body["conversation_id"]}
    assert httpx.post(services["backend"] + "/api/tickets/confirm", json=payload).status_code == 400
    payload["confirmed"] = True
    assert (
        httpx.post(services["backend"] + "/api/tickets/confirm", json=payload).json()["ticket"][
            "status"
        ]
        == "created"
    )


def test_degraded_secondary_preserves_alarm_and_rag_results(services):
    body = ask(
        services, "Investigate recurring alarms for Boiler Feed Pump 101", degraded_demo=True
    )
    assert body["status"] == "partial" and body["sources"] and body["facts"]["summary"]
    assert body["warnings"] and body["timeline"][-1]["status"] == "failed"
    assert body["facts"]["maintenance"] is None


def test_missing_and_ambiguous_assets_and_empty_range(services):
    assert ask(services, "hello")["status"] == "needs_input"
    assert ask(services, "Investigate Boiler Feed Pump 999")["status"] == "empty"
    assert ask(services, "Investigate compressor")["status"] == "needs_input"
    body = ask(services, "Boiler Feed Pump 101 from 2000-01-01 to 2000-02-01")
    assert body["status"] == "empty" and body["actions"] == []
    assert "No alarm events" in body["answer"]


@pytest.mark.parametrize(
    "message,key",
    [
        ("Calculate operator response efficiency for Compressor 202", "efficiency"),
        ("Show alarm trends for Motor 501", "trend"),
        ("Find flood alarms on Boiler Feed Pump 102", "flood"),
        ("Rationalize stale alarms for Control Valve 401", "rationalization"),
        ("Highest-priority alarm for Boiler Feed Pump 101", "priority"),
    ],
)
def test_multiple_intents_and_assets(services, message, key):
    body = ask(services, message)
    assert body["status"] == "complete"
    assert body["facts"][key]


def test_input_validation_and_frontend(services):
    assert httpx.post(services["backend"] + "/api/chat", json={"message": ""}).status_code == 422
    assert (
        httpx.post(
            services["backend"] + "/api/chat", json={"message": "hi", "conversation_id": "../bad"}
        ).status_code
        == 422
    )
    assert "Operations Atlas" in httpx.get(services["backend"]).text
    tools = httpx.get(services["backend"] + "/api/tools").json()["tools"]
    assert len(tools) == 17
