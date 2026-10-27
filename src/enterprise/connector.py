"""Only the Alarm MCP server imports this connector."""

import asyncio
from uuid import uuid4

import httpx
from mcp.server.fastmcp.exceptions import ToolError

from enterprise.config import API_TOKEN, API_URL, TIMEOUT
from enterprise.models import ToolResult


async def api_call(method: str, path: str, *, params=None, body=None, trace_id="", transport=None):
    trace = trace_id or str(uuid4())
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "trace_id": trace,
        "x-client-id": "alarm-mcp",
        "x-metadata-tag": "copilot",
    }
    async with httpx.AsyncClient(
        base_url=API_URL, timeout=TIMEOUT, headers=headers, transport=transport
    ) as client:
        for attempt in range(3):
            try:
                response = await client.request(method, path, params=params, json=body)
                if response.status_code in (429, 502, 503, 504) and attempt < 2:
                    await asyncio.sleep(0.1 * 2**attempt)
                    continue
                if response.is_error:
                    labels = {
                        401: "Authentication failed",
                        403: "Operation forbidden",
                        404: "Resource not found",
                        422: "Invalid API input",
                    }
                    raise ToolError(
                        f"{labels.get(response.status_code, 'Source unavailable')} (HTTP {response.status_code}); trace={trace}"
                    )
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ToolError(f"Invalid source response; trace={trace}")
                return ToolResult(
                    data=payload, trace_id=trace, api_status=response.status_code, retries=attempt
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 2:
                    raise ToolError(f"Source timeout or connection failure; trace={trace}") from exc
                await asyncio.sleep(0.1 * 2**attempt)
            except ValueError as exc:
                raise ToolError(f"Invalid source JSON; trace={trace}") from exc
    raise ToolError("Source unavailable")
