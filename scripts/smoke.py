import httpx

base = "http://127.0.0.1:8080"
health = httpx.get(base + "/health").json()
assert health["status"] == "ok" and health["tools"] == 17
r = httpx.post(
    base + "/api/chat",
    json={
        "message": "Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last 90 days"
    },
    timeout=30,
)
r.raise_for_status()
data = r.json()
assert data["status"] == "complete" and data["sources"]
assert {e["server"] for e in data["timeline"]} == {"alarm", "workorders"}
assert data["facts"]["summary"]["totals"]["alarm_count"] > 0
print("PASS: real MCP + API + maintenance + RAG combined workflow")
