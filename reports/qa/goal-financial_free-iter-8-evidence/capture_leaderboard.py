#!/usr/bin/env python3
"""Capture REAL pixels of the AutoSessionLeaderboard component rendering (J-16).

Uses Playwright in its OWN dedicated Chromium context. Unlike a backgrounded
Chrome-MCP tab (which reports visibilityState:'hidden' and starves the React 18
scheduler / poll timers — the documented hidden-tab render throttle), a dedicated
Playwright browser paints normally, so the data-loaded leaderboard frame sustains
and can be screenshotted.

It drives the LIVE app (http://localhost:3691). The app auto-opens the most-
recently-accessed session (App.tsx selects sorted-by-lastAccessedAt[0]); the seed
script makes the J-16 proof session the most recent, so it opens by default — no
DOM clicking. The screenshot is the actual component rendered through the normal
GET /api/sessions/{id} -> React render path (NOT an endpoint/JSON substitute).

API RELAY: the dev frontend instance currently bound to :3691 was started with a
backend URL pointing at a dead port, so its built-in Vite /api proxy 500s. To
capture against the healthy backend WITHOUT disturbing the running services, this
script relays the browser's same-origin /api/* calls to the known-good backend
(:8691). The component, data, and render path are unchanged — only the transport
hop is supplied by Playwright instead of Vite's misconfigured proxy. (In the
automated pipeline, browser-qa-phase.sh self-heals this by killing the stale
frontend and restarting it wired to the reconciled backend port.)

Run with system python3 (has playwright 1.58 + cached chromium):
    python3 reports/qa/goal-financial_free-iter-8-evidence/capture_leaderboard.py <out_basename> [expect_rejection]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3691"
BACKEND = "http://localhost:8691"  # confirmed-healthy backend
OUT_DIR = Path(__file__).resolve().parent
out_base = sys.argv[1] if len(sys.argv) > 1 else "J-16-leaderboard"
expect_rejection = (len(sys.argv) > 2 and sys.argv[2] == "expect_rejection")


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1680, "height": 1050}, device_scale_factor=2)

        # Relay same-origin /api/* to the healthy backend.
        def _relay(route):
            req = route.request
            target = req.url.replace(FRONTEND, BACKEND)
            headers = {k: v for k, v in req.headers.items() if k.lower() != "host"}
            try:
                resp = ctx.request.fetch(
                    target, method=req.method, headers=headers, data=req.post_data
                )
                route.fulfill(response=resp)
            except Exception as exc:  # pragma: no cover - diagnostic only
                print(f"[capture] relay error for {target}: {exc}", file=sys.stderr)
                route.abort()

        ctx.route("**/api/**", _relay)

        page = ctx.new_page()
        # Regression guard: the legacy-autoRun-without-budget crash blanked the
        # whole app (App.tsx mounts a useBacktest per session). Catch any uncaught
        # exception so this capture doubles as a no-crash regression test.
        page_errors: list[str] = []
        page.on("pageerror", lambda e: page_errors.append(str(e).split("\n")[0]))
        page.goto(FRONTEND, wait_until="networkidle", timeout=60000)

        # Wait for the real leaderboard to paint its rows.
        page.get_by_text("Candidate leaderboard").first.wait_for(timeout=45000)
        page.get_by_text("BEST", exact=True).first.wait_for(timeout=15000)
        page.wait_for_timeout(1500)  # let the iteration-join (WFE chips/metrics) settle

        container = page.get_by_text("Candidate leaderboard").first.locator(
            "xpath=ancestor::div[contains(@class,'rounded-lg')][1]"
        )
        container.scroll_into_view_if_needed()
        page.wait_for_timeout(300)

        # Use rendered text (inner_text) — page.content() HTML-escapes the "<" in
        # the WFE gating reason, so check the painted text instead.
        text = container.inner_text()
        checks = {
            "no app crash (pageerror)": len(page_errors) == 0,
            "Candidate leaderboard header": "Candidate leaderboard" in text,
            "BEST badge": "BEST" in text,
            "WFE chip": "WFE" in text,
        }
        if expect_rejection:
            checks["WFE rejection reason"] = "WFE 0.10 < 0.30" in text

        container.screenshot(path=str(OUT_DIR / f"{out_base}-component.png"))
        page.screenshot(path=str(OUT_DIR / f"{out_base}-fullpage.png"), full_page=True)
        if page_errors:
            print("[capture] PAGEERRORS:", sorted(set(page_errors)), file=sys.stderr)

        ok = all(checks.values())
        print(f"[capture] {out_base}: " + ", ".join(f"{k}={v}" for k, v in checks.items()))
        print(f"[capture] saved {out_base}-component.png and {out_base}-fullpage.png")
        ctx.close()
        browser.close()
        return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
