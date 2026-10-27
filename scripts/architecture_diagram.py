"""Render the architecture from local SVG, without an external rendering service."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
NODES = [
    (70, 100, 270, 85, "Responsive chat GUI", "Citations · schemas · timeline", "#e8efdf"),
    (450, 100, 380, 85, "Copilot orchestration", "Intent · context · approval boundary", "#dceadd"),
    (
        450,
        270,
        380,
        85,
        "Official MCP client / registry",
        "Discovery · schemas · trace IDs",
        "#dceadd",
    ),
    (70, 450, 310, 85, "Alarm management MCP", "Independent stdio process", "#dceadd"),
    (470, 450, 310, 85, "Work orders MCP", "Independent stdio process", "#dceadd"),
    (70, 650, 310, 85, "Alarm Management API", "HTTP bearer + trace headers", "#efe9d8"),
    (
        470,
        650,
        310,
        85,
        "SQLite enterprise source",
        "Maintenance · drafts · approved tickets",
        "#efe9d8",
    ),
    (
        970,
        100,
        340,
        85,
        "Markdown document store",
        "Synthetic corpus + revision metadata",
        "#eee8d9",
    ),
    (
        970,
        270,
        340,
        85,
        "Ingestion pipeline",
        "Extract · chunk · quarantine instructions",
        "#eee8d9",
    ),
    (970, 450, 340, 85, "Sparse retrieval index", "TF-IDF cosine + lexical coverage", "#eee8d9"),
    (
        970,
        650,
        340,
        85,
        "Filtered retrieval / composer",
        "Grounded excerpts + citations",
        "#eee8d9",
    ),
    (
        350,
        820,
        620,
        65,
        "Observability",
        "Shared trace · server/tool · status · retries · duration",
        "#e8ece7",
    ),
]
parts = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="940" viewBox="0 0 1400 940"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0 0L0 6L8 3Z" fill="#587260"/></marker></defs><rect width="1400" height="940" fill="#f7f8f3"/><text x="65" y="47" font-family="sans-serif" font-size="25" fill="#18352b">OPERATIONS ATLAS / MCP + RAG architecture</text>'
]
for x1, y1, x2, y2 in [
    (340, 142, 450, 142),
    (640, 185, 640, 270),
    (530, 355, 225, 450),
    (700, 355, 625, 450),
    (225, 535, 225, 650),
    (625, 535, 625, 650),
    (1140, 185, 1140, 270),
    (1140, 355, 1140, 450),
    (1140, 535, 1140, 650),
    (970, 690, 830, 142),
    (225, 735, 500, 820),
    (625, 735, 625, 820),
]:
    parts.append(
        f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#587260" stroke-width="2" fill="none" marker-end="url(#arrow)"/>'
    )
for x, y, w, h, title, sub, color in NODES:
    parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{color}" stroke="#bdcdbc"/><text x="{x + w / 2}" y="{y + 33}" font-family="sans-serif" font-size="17" text-anchor="middle" fill="#17362b">{title}</text><text x="{x + w / 2}" y="{y + 57}" font-family="sans-serif" font-size="12" text-anchor="middle" fill="#607564">{sub}</text>'
    )
parts.append(
    '<text x="80" y="405" font-family="sans-serif" font-size="13" fill="#587260">TRUSTED LOCAL STDIO BOUNDARY / JSON-RPC</text><text x="950" y="790" font-family="sans-serif" font-size="12" fill="#587260">UNTRUSTED DOCUMENT EVIDENCE / NO TOOL AUTHORITY</text></svg>'
)
path = ROOT / "docs/architecture-diagram.svg"
path.write_text("".join(parts))
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1400, "height": 940}, device_scale_factor=1)
    page.set_content(path.read_text())
    page.screenshot(path=str(ROOT / "docs/architecture-diagram.png"))
    browser.close()
