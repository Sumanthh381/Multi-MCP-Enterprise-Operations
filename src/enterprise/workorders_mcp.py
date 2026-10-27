"""Second independently runnable MCP server; SQLite maintenance and approved drafts."""

import json
import sqlite3
from typing import Annotated
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from enterprise.config import DATABASE
from enterprise.models import ToolResult

mcp = FastMCP("work-orders")


def database():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, draft_id TEXT UNIQUE, body TEXT NOT NULL)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS maintenance (asset_id TEXT PRIMARY KEY, body TEXT NOT NULL)"
    )
    for asset in (
        "BFP-101",
        "BFP-102",
        "CMP-201",
        "CMP-202",
        "CMP-203",
        "MOT-501",
        "MOT-502",
        "MOT-503",
        "VAL-401",
    ):
        conn.execute(
            "INSERT OR IGNORE INTO maintenance VALUES (?, ?)",
            (
                asset,
                json.dumps(
                    {
                        "work_order_id": f"WO-{asset}",
                        "asset_id": asset,
                        "date": "2026-05-15",
                        "finding": "Suction strainer fouling observed; bearing alignment verification pending",
                        "status": "inspection due",
                        "synthetic": True,
                    }
                ),
            ),
        )
    conn.commit()
    return conn


@mcp.tool()
def maintenance_history(
    asset_id: Annotated[str, Field(min_length=1, max_length=100)], trace_id: str = ""
) -> ToolResult:
    """Read persisted maintenance history for a resolved alarm asset identifier."""
    with database() as conn:
        row = conn.execute(
            "SELECT body FROM maintenance WHERE asset_id = ?", (asset_id,)
        ).fetchone()
    return ToolResult(
        data={"records": [json.loads(row[0])] if row else []}, trace_id=trace_id or str(uuid4())
    )


@mcp.tool()
def prepare_issue_draft(
    asset_id: Annotated[str, Field(min_length=1, max_length=100)],
    title: Annotated[str, Field(min_length=1, max_length=200)],
    evidence: Annotated[str, Field(min_length=1, max_length=12000)],
    trace_id: str = "",
) -> ToolResult:
    """Prepare a local escalation draft. Does not create a ticket or contact GitHub."""
    draft = {
        "draft_id": str(uuid4()),
        "asset_id": asset_id,
        "title": title,
        "evidence": evidence,
        "status": "awaiting_confirmation",
    }
    with database() as conn:
        conn.execute("INSERT INTO drafts VALUES (?, ?)", (draft["draft_id"], json.dumps(draft)))
    return ToolResult(data=draft, trace_id=trace_id or str(uuid4()))


@mcp.tool()
def create_ticket(draft_id: str, confirmed: bool = False, trace_id: str = "") -> ToolResult:
    """Create one local mock ticket from a persisted draft only after explicit user confirmation."""
    if not confirmed:
        raise ToolError("Explicit user confirmation required")
    with database() as conn:
        draft = conn.execute("SELECT body FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if not draft:
            raise ToolError("Draft not found")
        existing = conn.execute("SELECT id FROM tickets WHERE draft_id = ?", (draft_id,)).fetchone()
        ticket_id = existing[0] if existing else f"TKT-{uuid4().hex[:10]}"
        conn.execute(
            "INSERT OR IGNORE INTO tickets VALUES (?, ?, ?)", (ticket_id, draft_id, draft[0])
        )
    return ToolResult(
        data={"ticket_id": ticket_id, "draft_id": draft_id, "status": "created", "mock": True},
        trace_id=trace_id or str(uuid4()),
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
