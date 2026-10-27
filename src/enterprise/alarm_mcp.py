"""Real MCP server over stdio; start with python -m enterprise.alarm_mcp."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from enterprise.connector import api_call
from enterprise.models import (
    AlarmRequest,
    CorrelationRequest,
    ExecuteRequest,
    FloodRequest,
    GenerateRequest,
    RationalizationRequest,
    RecommendationRequest,
    SummaryRequest,
    ToolResult,
    TrendsRequest,
)

mcp = FastMCP("alarm-management")
ID = Annotated[str, Field(min_length=1, max_length=100)]
Trace = Annotated[str, Field(max_length=128)]


@mcp.tool()
async def search_assets(
    query: Annotated[str, Field(min_length=1, max_length=200)],
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
    unit: str | None = None,
    trace_id: Trace = "",
) -> ToolResult:
    """Resolve an asset name to identifiers; optionally restrict to a plant unit."""
    return await api_call(
        "GET",
        "/assets/search",
        params={
            k: v for k, v in {"query": query, "limit": limit, "unit": unit}.items() if v is not None
        },
        trace_id=trace_id,
    )


@mcp.tool()
async def asset_metadata(asset_id: ID, trace_id: Trace = "") -> ToolResult:
    """Read criticality, unit and site metadata for a resolved asset."""
    return await api_call("GET", f"/assets/{asset_id}/metadata", trace_id=trace_id)


@mcp.tool()
async def get_alarms(
    asset_id: ID,
    start_time: str | None = None,
    end_time: str | None = None,
    severity: str | None = None,
    page: Annotated[int, Field(ge=1)] = 1,
    page_size: Annotated[int, Field(ge=1, le=200)] = 50,
    trace_id: Trace = "",
) -> ToolResult:
    """Retrieve one page of asset alarms. Follow total_pages to retrieve remaining pages."""
    params = {k: v for k, v in locals().items() if k != "trace_id" and v is not None}
    return await api_call("GET", "/alarms", params=params, trace_id=trace_id)


@mcp.tool()
async def alarm_detail(alarm_id: ID, trace_id: Trace = "") -> ToolResult:
    """Retrieve an alarm by identifier."""
    return await api_call("GET", f"/alarms/{alarm_id}", trace_id=trace_id)


# Explicit typed signatures preserve input/output schemas in MCP discovery.
@mcp.tool()
async def alarm_summary(request: SummaryRequest, trace_id: Trace = "") -> ToolResult:
    """Aggregate filtered alarms by selected dimensions and KPIs."""
    return await api_call(
        "POST", "/alarms/summary", body=request.model_dump(mode="json"), trace_id=trace_id
    )


@mcp.tool()
async def alarm_trends(request: TrendsRequest, trace_id: Trace = "") -> ToolResult:
    """Bucket alarm counts or acknowledgement delays over time."""
    return await api_call(
        "POST", "/alarms/trends", body=request.model_dump(mode="json"), trace_id=trace_id
    )


@mcp.tool()
async def correlate_alarms(request: CorrelationRequest, trace_id: Trace = "") -> ToolResult:
    """Find time-window co-occurrences; correlation does not prove causation."""
    return await api_call(
        "POST", "/alarms/correlation", body=request.model_dump(mode="json"), trace_id=trace_id
    )


@mcp.tool()
async def flood_analysis(request: FloodRequest, trace_id: Trace = "") -> ToolResult:
    """Identify rolling alarm floods above a configurable event threshold."""
    return await api_call(
        "POST", "/alarms/flood-analysis", body=request.model_dump(mode="json"), trace_id=trace_id
    )


@mcp.tool()
async def rationalization_candidates(
    request: RationalizationRequest, trace_id: Trace = ""
) -> ToolResult:
    """Find recurrent or stale alarms requiring engineering review; never suppress them."""
    return await api_call(
        "POST",
        "/alarms/rationalization-candidates",
        body=request.model_dump(mode="json"),
        trace_id=trace_id,
    )


@mcp.tool()
async def priority_score(request: AlarmRequest, trace_id: Trace = "") -> ToolResult:
    """Score an alarm using severity and asset criticality."""
    return await api_call(
        "POST", "/alarms/priority-score", body=request.model_dump(mode="json"), trace_id=trace_id
    )


@mcp.tool()
async def operator_recommendations(
    request: RecommendationRequest, trace_id: Trace = ""
) -> ToolResult:
    """Read advisory operator actions and optional related asset/alarm context."""
    return await api_call(
        "POST",
        "/recommendations/operator-actions",
        body=request.model_dump(mode="json"),
        trace_id=trace_id,
    )


@mcp.tool()
async def generate_calculation(request: GenerateRequest, trace_id: Trace = "") -> ToolResult:
    """Register an allowlisted KPI formula and return its calculation identifier."""
    return await api_call(
        "POST",
        "/calculation-code/generate",
        body=request.model_dump(mode="json"),
        trace_id=trace_id,
    )


@mcp.tool()
async def execute_calculation(request: ExecuteRequest, trace_id: Trace = "") -> ToolResult:
    """Evaluate a previously registered KPI formula; arbitrary code is prohibited."""
    return await api_call(
        "POST", "/calculation-code/execute", body=request.model_dump(mode="json"), trace_id=trace_id
    )


@mcp.tool()
async def kpi_definitions(trace_id: Trace = "") -> ToolResult:
    """Read documented KPI formulas and measurement definitions."""
    return await api_call("GET", "/analytics/kpi-definitions", trace_id=trace_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
