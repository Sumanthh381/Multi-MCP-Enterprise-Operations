from enterprise.orchestrator import Copilot
from enterprise.rag import Retrieval
from enterprise.registry import Registry


async def test_no_document_evidence_withholds_recommendations(services, monkeypatch):
    monkeypatch.setenv("ALARM_API_BASE_URL", services["api"])
    monkeypatch.setenv("DATA_PATH", services["env"]["DATA_PATH"])
    registry = await Registry().connect()
    try:
        result = await Copilot(registry, Retrieval([])).run("Investigate Boiler Feed Pump 101")
        assert result["status"] == "partial"
        assert not result["sources"] and not result["actions"]
        assert "withheld" in result["warnings"][0]
    finally:
        await registry.close()
