import pytest

from enterprise.orchestrator import Copilot
from enterprise.rag import Retrieval, ingest
from enterprise.registry import ToolFailure


class FailureRegistry:
    async def call(self, *args):
        raise ToolFailure("Authentication failed (HTTP 401)")


async def test_required_source_failure_is_explicit():
    result = await Copilot(FailureRegistry(), Retrieval(ingest())).run(
        "Investigate Boiler Feed Pump 101"
    )
    assert result["status"] == "failed"
    assert "Authentication failed" in result["answer"]
    assert not result["actions"] and not result["sources"]


async def test_ticket_requires_matching_conversation():
    copilot = Copilot(FailureRegistry(), Retrieval([]))
    copilot.pending["d"] = "correct"
    with pytest.raises(ToolFailure, match="this conversation"):
        await copilot.confirm("d", "incorrect", True)
    with pytest.raises(ToolFailure, match="this conversation"):
        await copilot.confirm("d", "correct", False)
