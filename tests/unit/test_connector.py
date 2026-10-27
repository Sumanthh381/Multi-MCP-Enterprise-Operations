import httpx
import pytest
from mcp.server.fastmcp.exceptions import ToolError

from enterprise.connector import api_call


async def test_retry_headers_and_success():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) < 3 else 200, json={"results": []})

    result = await api_call(
        "GET", "/assets/search", trace_id="trace-123", transport=httpx.MockTransport(handler)
    )
    assert result.retries == 2 and len(calls) == 3
    assert calls[0].headers["trace_id"] == "trace-123"
    assert calls[0].headers["Authorization"] == "Bearer demo-token"
    assert calls[0].headers["x-client-id"] == "alarm-mcp"


@pytest.mark.parametrize(
    "status,expected",
    [
        (401, "Authentication"),
        (403, "forbidden"),
        (404, "not found"),
        (422, "Invalid"),
        (500, "unavailable"),
    ],
)
async def test_api_error_mapping_and_no_secret_leak(status, expected):
    with pytest.raises(ToolError, match=expected) as exc:
        await api_call(
            "GET",
            "/bad",
            transport=httpx.MockTransport(
                lambda _: httpx.Response(status, text="secret-token-should-not-escape")
            ),
        )
    assert "secret-token" not in str(exc.value)


async def test_timeout_retries_are_bounded():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("sensitive details")

    with pytest.raises(ToolError, match="timeout"):
        await api_call("GET", "/bad", transport=httpx.MockTransport(handler))
    assert len(calls) == 3


async def test_malformed_output():
    with pytest.raises(ToolError, match="Invalid source JSON"):
        await api_call(
            "GET",
            "/bad",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, text="not json")),
        )
    with pytest.raises(ToolError, match="Invalid source response"):
        await api_call(
            "GET", "/bad", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[]))
        )
