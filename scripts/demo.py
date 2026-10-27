"""Capture genuine browser evidence; requires Chromium and Playwright's FFmpeg."""

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence"


async def main():
    EVIDENCE.mkdir(exist_ok=True, parents=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"), args=["--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1080},
            record_video_dir=str(EVIDENCE / "raw-video"),
            record_video_size={"width": 1440, "height": 1080},
        )
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:8080")
        await page.get_by_text("2 MCP servers connected", exact=False).wait_for()
        await page.screenshot(path=str(EVIDENCE / "01-workspace.png"), full_page=True)
        await page.wait_for_timeout(2000)
        await page.locator("#tools details").first.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(EVIDENCE / "02-discovery-schemas.png"), full_page=True)
        await page.locator("#tools details").first.click()
        await page.locator("#prompt").fill(
            "Investigate recurring high-severity alarms for Boiler Feed Pump 101 over the last 90 days, identify contributing factors, retrieve the operating procedure and prepare an issue draft"
        )
        await page.locator("#send").click()
        await page.locator(".status").last.wait_for()
        assert await page.locator(".status").last.inner_text() == "COMPLETE"
        assert await page.locator(".source").count() > 0
        assert await page.locator(".event").count() >= 8
        await page.screenshot(path=str(EVIDENCE / "03-investigation.png"), full_page=True)
        await page.wait_for_timeout(2500)
        await page.locator("#timeline").scroll_into_view_if_needed()
        await page.locator("#timeline details").first.click()
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(EVIDENCE / "04-execution-trace.png"), full_page=True)
        await page.locator("#evidence").scroll_into_view_if_needed()
        await page.wait_for_timeout(2500)
        await page.locator(".confirm").click()
        await page.get_by_text("Created TKT-", exact=False).wait_for()
        await page.wait_for_timeout(1800)
        await page.locator("#degraded").check()
        await page.locator("#prompt").fill("Investigate recurring alarms for Boiler Feed Pump 101")
        await page.locator("#send").click()
        await page.locator(".status.partial").wait_for()
        assert await page.locator(".event.failed").count() == 1
        await page.screenshot(path=str(EVIDENCE / "05-degraded.png"), full_page=True)
        await page.wait_for_timeout(2500)
        await page.locator("#evidence").scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.screenshot(path=str(EVIDENCE / "06-mobile.png"), full_page=True)
        assert not errors, errors
        video = page.video
        await context.close()
        await video.save_as(str(EVIDENCE / "demo.webm"))
        await browser.close()
        print(
            "PASS: browser discovery, combined investigation, citations, approval, degraded state, mobile; video saved"
        )


if __name__ == "__main__":
    asyncio.run(main())
