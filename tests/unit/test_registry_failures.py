import pytest
from mcp.types import CallToolResult, Tool

from enterprise.registry import Registry, ToolFailure


class BadSession:
    def __init__(self, timeout):
        self.timeout = timeout

    async def call_tool(self, *args, **kwargs):
        if self.timeout:
            raise TimeoutError("internal sensitive transport detail")
        return CallToolResult(
            content=[], structuredContent={"data": {"count": "not-an-integer"}, "trace_id": "x"}
        )


@pytest.mark.parametrize("timeout", [False, True])
async def test_transport_and_malformed_output_fail_safely(timeout):
    r = Registry()
    r.sessions["alarm"] = BadSession(timeout)
    r.tools["alarm.example"] = Tool(
        name="example",
        inputSchema={"type": "object"},
        outputSchema={
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {"count": {"type": "integer"}},
                    "required": ["count"],
                }
            },
            "required": ["data"],
        },
    )
    timeline = []
    with pytest.raises(ToolFailure) as exc:
        await r.call("alarm.example", {}, "test-output", timeline)
    assert "sensitive" not in str(exc.value)
    assert timeline[0]["status"] == "failed"
    assert "duration_ms" in timeline[0]
