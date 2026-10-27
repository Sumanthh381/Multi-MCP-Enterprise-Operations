"""Schema-aware official MCP client. No direct source API access."""

import json
import logging
import os
import sys
import time
from contextlib import AsyncExitStack
from datetime import timedelta

from jsonschema import ValidationError, validate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from enterprise.config import ROOT
from enterprise.models import ToolResult

log = logging.getLogger("mcp-client")


class ToolFailure(Exception):
    pass


class Registry:
    def __init__(self):
        self.sessions = {}
        self.tools = {}
        self.unavailable = {}
        self.stack = AsyncExitStack()

    async def connect(self):
        # Local stdio is the authorization boundary: children inherit only required config.
        allowed = {
            "PATH",
            "SYSTEMROOT",
            "ALARM_API_BASE_URL",
            "ALARM_API_TOKEN",
            "API_TIMEOUT_SECONDS",
            "DATA_PATH",
            "ENTERPRISE_ROOT",
            "COVERAGE_PROCESS_CONFIG",
        }
        child_env = {k: v for k, v in os.environ.items() if k in allowed}
        for server, module in (
            ("alarm", "enterprise.alarm_mcp"),
            ("workorders", "enterprise.workorders_mcp"),
        ):
            try:
                read, write = await self.stack.enter_async_context(
                    stdio_client(
                        StdioServerParameters(
                            command=sys.executable, args=["-m", module], env=child_env, cwd=ROOT
                        )
                    )
                )
                session = await self.stack.enter_async_context(
                    ClientSession(read, write, read_timeout_seconds=timedelta(seconds=20))
                )
                await session.initialize()
                discovered = await session.list_tools()
                self.sessions[server] = session
                for tool in discovered.tools:
                    self.tools[f"{server}.{tool.name}"] = tool
            except Exception:
                self.unavailable[server] = "MCP server unavailable"
        return self

    async def close(self):
        await self.stack.aclose()

    def catalog(self):
        return [
            {"key": k, "server": k.split(".")[0], **t.model_dump(mode="json")}
            for k, t in self.tools.items()
        ]

    async def call(self, key, arguments, trace, timeline):
        started = time.monotonic()
        event = {
            "server": key.split(".")[0],
            "tool": key,
            "input": arguments,
            "trace_id": trace,
            "status": "running",
        }
        timeline.append(event)
        try:
            if key not in self.tools:
                raise ToolFailure(f"Unavailable tool: {key}")
            args = {**arguments, "trace_id": trace}
            validate(args, self.tools[key].inputSchema)
            result = await self.sessions[event["server"]].call_tool(
                key.split(".")[1],
                args,
                read_timeout_seconds=timedelta(seconds=20),
                meta={"trace_id": trace},
            )
            if result.isError:
                raise ToolFailure("; ".join(c.text for c in result.content if c.type == "text"))
            output = result.structuredContent
            if output is None:
                output = json.loads(next(c.text for c in result.content if c.type == "text"))
            if self.tools[key].outputSchema:
                validate(output, self.tools[key].outputSchema)
            envelope = ToolResult.model_validate(output)
            event.update(
                status="success",
                output=envelope.data,
                api_status=envelope.api_status,
                retries=envelope.retries,
            )
            return envelope.data
        except ValidationError as exc:
            event.update(status="failed", error="Invalid tool arguments or output schema")
            raise ToolFailure(event["error"]) from exc
        except Exception as exc:
            message = (
                str(exc) if isinstance(exc, ToolFailure) else "MCP transport failure or timeout"
            )
            event.update(status="failed", error=message)
            raise ToolFailure(message) from exc
        finally:
            event["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
            log.info(json.dumps({k: v for k, v in event.items() if k not in ("input", "output")}))
