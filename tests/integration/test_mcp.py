import pytest

from enterprise.registry import Registry, ToolFailure


async def test_real_mcp_discovery_chaining_validation_and_errors(services, monkeypatch):
    for k, v in services["env"].items():
        if k in ("ALARM_API_BASE_URL", "DATA_PATH"):
            monkeypatch.setenv(k, v)
    r = await Registry().connect()
    timeline = []
    try:
        assert len(r.sessions) == 2 and len(r.tools) == 17
        assert all(t.inputSchema and t.outputSchema for t in r.tools.values())
        found = await r.call(
            "alarm.search_assets", {"query": "Boiler Feed Pump 101"}, "integration-trace", timeline
        )
        asset_id = found["results"][0]["asset_id"]
        alarms = await r.call(
            "alarm.get_alarms",
            {"asset_id": asset_id, "page_size": 1},
            "integration-trace",
            timeline,
        )
        assert alarms["total_pages"] > 1
        history = await r.call(
            "workorders.maintenance_history", {"asset_id": asset_id}, "integration-trace", timeline
        )
        assert history["records"][0]["asset_id"] == asset_id
        assert all(e["trace_id"] == "integration-trace" for e in timeline)
        with pytest.raises(ToolFailure, match="Invalid tool arguments"):
            await r.call("alarm.get_alarms", {"asset_id": asset_id, "page": 0}, "t", timeline)
        with pytest.raises(ToolFailure, match="Unavailable tool"):
            await r.call("alarm.missing", {}, "t", timeline)
        with pytest.raises(ToolFailure, match="not found"):
            await r.call("alarm.alarm_detail", {"alarm_id": "missing"}, "t", timeline)
        draft = await r.call(
            "workorders.prepare_issue_draft",
            {"asset_id": asset_id, "title": "Test escalation", "evidence": "[SOP-PUMP-101:1:0]"},
            "t",
            timeline,
        )
        with pytest.raises(ToolFailure, match="confirmation"):
            await r.call("workorders.create_ticket", {"draft_id": draft["draft_id"]}, "t", timeline)
        ticket = await r.call(
            "workorders.create_ticket",
            {"draft_id": draft["draft_id"], "confirmed": True},
            "t",
            timeline,
        )
        again = await r.call(
            "workorders.create_ticket",
            {"draft_id": draft["draft_id"], "confirmed": True},
            "t",
            timeline,
        )
        assert ticket == again
        injected = await r.call(
            "workorders.maintenance_history", {"asset_id": "' OR 1=1 --"}, "t", timeline
        )
        assert injected["records"] == []
    finally:
        await r.close()


async def test_every_alarm_tool_over_real_mcp(services, monkeypatch):
    monkeypatch.setenv("ALARM_API_BASE_URL", services["api"])
    monkeypatch.setenv("DATA_PATH", services["env"]["DATA_PATH"])
    r = await Registry().connect()
    events = []
    try:
        a = await r.call("alarm.get_alarms", {"asset_id": "BFP-101"}, "all-tools", events)
        alarm_id = a["data"][0]["alarm_id"]
        args = {
            "asset_metadata": {"asset_id": "BFP-101"},
            "alarm_detail": {"alarm_id": alarm_id},
            "alarm_summary": {"request": {"asset_ids": ["BFP-101"]}},
            "alarm_trends": {"request": {"asset_ids": ["BFP-101"]}},
            "correlate_alarms": {"request": {"asset_ids": ["BFP-101"]}},
            "flood_analysis": {"request": {"unit": "Unit 2"}},
            "rationalization_candidates": {"request": {"asset_ids": ["BFP-101"]}},
            "priority_score": {"request": {"alarm_id": alarm_id}},
            "operator_recommendations": {"request": {"alarm_id": alarm_id}},
            "kpi_definitions": {},
        }
        for tool, body in args.items():
            assert await r.call("alarm." + tool, body, "all-tools", events)
        generated = await r.call(
            "alarm.generate_calculation",
            {"request": {"calculation_type": "operator_response_efficiency"}},
            "all-tools",
            events,
        )
        out = await r.call(
            "alarm.execute_calculation",
            {"request": {"calculation_id": generated["calculation_id"]}},
            "all-tools",
            events,
        )
        assert out["sample_count"] > 0
    finally:
        await r.close()
