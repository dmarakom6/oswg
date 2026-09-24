#!/usr/bin/env python3
"""Render docs/architecture.mmd to docs/architecture.png.

Uses Playwright (the `js` extra) to run Mermaid in a headless browser and
screenshot the result. Requires:

    pip install -e '.[js]'
    playwright install chromium

Usage:  python3 docs/render_architecture.py
"""

from __future__ import annotations

import html
from pathlib import Path

DOCS = Path(__file__).resolve().parent
SRC = DOCS / "architecture.mmd"
OUT = DOCS / "architecture.png"

# Mermaid ESM build from a CDN. Swap for a local copy if running offline.
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 20px; background: #ffffff; }}
  .mermaid {{ font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
</style>
</head><body>
<pre class="mermaid">{diagram}</pre>
<script type="module">
  import mermaid from "{cdn}";
  mermaid.initialize({{ startOnLoad: true, theme: "base", flowchart: {{ htmlLabels: true, curve: "basis", padding: 12 }} }});
</script>
</body></html>
"""


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed: pip install -e '.[js]'", file=__import__("sys").stderr)
        return 1

    diagram = SRC.read_text()
    tmp = DOCS / "_architecture.html"
    tmp.write_text(PAGE.format(diagram=html.escape(diagram), cdn=MERMAID_CDN))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(device_scale_factor=3, viewport={"width": 1700, "height": 1400})
        page.goto(tmp.as_uri())
        page.wait_for_selector("pre.mermaid svg", timeout=45000)
        page.wait_for_timeout(600)
        svg = page.query_selector("pre.mermaid svg")
        box = svg.bounding_box()
        svg.screenshot(path=str(OUT))
        browser.close()

    tmp.unlink(missing_ok=True)
    print(f"wrote {OUT} ({box['width']:.0f}x{box['height']:.0f} css px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())