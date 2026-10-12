"""Headless UI smoke test on synthetic data: every page, both widths, the full
onboarding with the dev demo connector. Fails on any console error or uncaught
exception. Needs the local API on :8080 in local mode (`uv run afterparty-dev`).
Never touches real data.

    uv run python scripts/ui_smoke.py
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import httpx
from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("AFTERPARTY_URL", "http://127.0.0.1:8080")
EMAIL = "ui-smoke@example.com"


def main() -> int:
    api = httpx.Client(base_url=BASE, timeout=30)
    me = {"Authorization": f"Dev {EMAIL}"}
    api.delete("/api/me", headers=me)
    api.get("/api/me", headers=me).raise_for_status()

    errors: list[str] = []

    def watch(page: Page, label: str) -> None:
        page.on(
            "console", lambda m: m.type == "error" and errors.append(f"{label}: {m.text[:200]}")
        )
        page.on("pageerror", lambda e: errors.append(f"{label}: {e}"))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, viewport in (
            ("desktop", {"width": 1280, "height": 860}),
            ("phone", {"width": 390, "height": 844}),
        ):
            page = browser.new_page(viewport=viewport, accept_downloads=True)
            watch(page, label)
            page.goto(f"{BASE}/")
            expect(
                page.get_by_role(
                    "heading", name="Sync your Partiful guest lists. Export them to CSV."
                )
            ).to_be_visible()
            page.goto(f"{BASE}/privacy")
            expect(page.get_by_role("heading", name="Privacy")).to_be_visible()
            page.goto(f"{BASE}/signin")
            page.evaluate(f"localStorage.setItem('ap.devEmail', '{EMAIL}')")
            if label == "desktop":
                page.goto(f"{BASE}/onboarding")
                page.get_by_role("button", name="Start setup").click()
                page.get_by_role("button", name="Continue").click()
                page.get_by_role("button", name="Use demo data").click()
                expect(page.get_by_text("Reading your guest lists")).to_be_visible(timeout=10000)
                expect(page.get_by_role("button", name="Open Afterparty")).to_be_visible(
                    timeout=30000
                )
                expect(page.get_by_text("You met")).to_be_visible(timeout=10000)
                page.get_by_role("button", name="Open Afterparty").click()
                page.wait_for_url("**/home")
                print("  ok  onboarding with the demo connector")
            for path, heading in (
                ("/home", "You met"),
                ("/people", "People"),
                ("/events", "Events"),
                ("/events/demo-ev-3", "Voice AI Builders Night"),
                ("/events/demo-ev-4", "Guest list hidden"),
                ("/settings", "Settings"),
            ):
                page.goto(f"{BASE}{path}")
                h = page.get_by_role("heading", name=heading).first
                expect(h).to_be_visible(timeout=10000)
            if label == "desktop":
                # Map by designation, then back to the list.
                page.goto(f"{BASE}/people?view=map")
                expect(page.get_by_role("img", name=re.compile("Map of"))).to_be_visible(
                    timeout=10000
                )
                # Multi-select export: tick two, export, and get a real CSV.
                page.goto(f"{BASE}/people")
                boxes = page.locator("li input[type=checkbox]")
                boxes.nth(0).check()
                boxes.nth(1).check()
                expect(page.get_by_text("2 selected")).to_be_visible()
                with page.expect_download() as dl:
                    page.get_by_role("button", name="Export CSV").click()
                text = Path(dl.value.path()).read_text(encoding="utf-8-sig")
                assert text.startswith("name,first_name"), text[:80]
                assert len(text.strip().splitlines()) >= 3, "expected 2 people in the export"
                # Export with a filter on.
                page.get_by_role("button", name="Any social").click()
                with page.expect_download() as dl:
                    page.get_by_role("button", name=re.compile(r"^Export \d")).click()
                assert Path(dl.value.path()).read_text(encoding="utf-8-sig").startswith("name,")
                page.goto(f"{BASE}/how-it-works#designation")
                expect(
                    page.get_by_role("heading", name="How a designation is decided")
                ).to_be_visible()
                print("  ok  map, multi-select export, filtered export, explainer")
            # The drawer: open, mark, note, close.
            page.goto(f"{BASE}/people")
            page.locator("li").first.click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="Contacted").click()
            dialog.locator("textarea").fill("smoke note")
            dialog.get_by_role("button", name="Close").first.click()
            time.sleep(0.5)
            no_overflow = page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert no_overflow, f"{label}: page scrolls sideways"
            print(f"  ok  every page on {label}, no sideways scroll")
            page.close()
        browser.close()

    api.delete("/api/me", headers=me)
    if errors:
        print("  FAIL console errors:")
        for e in errors:
            print("   ", e)
        return 1
    print("  ok  no console errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
