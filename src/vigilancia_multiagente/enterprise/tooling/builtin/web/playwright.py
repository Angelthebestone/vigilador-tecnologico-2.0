"""Playwright tool — native WRAP-SDK over the ``playwright`` Python package.

Spec 021 FR-053/054: native-first, universal Tool abstraction.
Catalog: ``playwright`` / domain ``research`` / capabilities
``[navigate, screenshot, click, fill]``.

Strategy: WRAP-SDK using the ``playwright`` Python package (optional
dependency; needs ``playwright install chromium`` once for the browser
binary). No network API; runs a headless Chromium subprocess.

Each ``execute()`` call uses a one-shot browser context (cold start
~500 ms). For long sessions we'd cache a Browser instance — out of scope
for the MVP reference port.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from vigilancia_multiagente.enterprise.governance.url_safety import is_safe_url
from vigilancia_multiagente.enterprise.tooling.tool_wrapper import HealthcheckResult

_DEFAULT_TIMEOUT_MS = 30000


@dataclass(frozen=True)
class PlaywrightTool:
    """Native tool for headless browser automation via Playwright."""

    name: str = "playwright"
    domain: str = "research"
    is_external_mcp: bool = False
    requires_auth: bool = False

    async def healthcheck(self) -> HealthcheckResult:
        """Verify the optional package is importable.

        Does not check the Chromium binary; if it's missing, ``execute()``
        raises with the install command in the error message.
        """
        try:
            import playwright  # noqa: F401  # presence-only import probe
        except ImportError:
            return HealthcheckResult(
                status="UNCONFIGURED",
                error=(
                    "playwright package not installed; run "
                    "`pip install playwright && playwright install chromium`"
                ),
            )
        return HealthcheckResult(status="UP")

    async def execute(
        self, tool_name: str, args: dict[str, object]
    ) -> dict[str, object]:
        """Dispatch to the requested capability.

        Supported ``tool_name`` values:
        * ``navigate`` — args: ``url`` (str, required). Returns the page
          HTML content + final URL.
        * ``screenshot`` — args: ``url`` (str), ``path`` (str, required).
          Saves a PNG to ``path`` and returns its size.
        * ``click`` — args: ``url`` (str), ``selector`` (str, required).
          Loads the page, clicks the selector, returns final URL.
        * ``fill`` — args: ``url`` (str), ``selector`` (str), ``value`` (str).
          Loads, fills the input, returns the field's resulting value.
        """
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("PlaywrightTool: 'url' must be a non-empty string")
        if not is_safe_url(url):
            raise PermissionError(
                f"PlaywrightTool: URL safety check rejected '{url}'"
            )

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "PlaywrightTool: playwright package not installed"
            ) from exc

        headless = (os.getenv("VT_PLAYWRIGHT_HEADLESS", "true").lower()
                    not in {"0", "false", "no"})

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            try:
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(url, timeout=_DEFAULT_TIMEOUT_MS)
                if tool_name == "navigate":
                    return {"url": page.url, "html": await page.content()}
                if tool_name == "screenshot":
                    path = args.get("path")
                    if not isinstance(path, str) or not path.strip():
                        raise ValueError("PlaywrightTool: 'path' required")
                    await page.screenshot(path=path, full_page=True)
                    return {"url": page.url, "screenshot_path": path}
                if tool_name == "click":
                    selector = args.get("selector")
                    if not isinstance(selector, str) or not selector.strip():
                        raise ValueError("PlaywrightTool: 'selector' required")
                    await page.click(selector, timeout=_DEFAULT_TIMEOUT_MS)
                    return {"url": page.url, "clicked": selector}
                if tool_name == "fill":
                    selector = args.get("selector")
                    value = args.get("value")
                    if not isinstance(selector, str) or not selector.strip():
                        raise ValueError("PlaywrightTool: 'selector' required")
                    if not isinstance(value, str):
                        raise ValueError("PlaywrightTool: 'value' must be a string")
                    await page.fill(selector, value, timeout=_DEFAULT_TIMEOUT_MS)
                    return {"url": page.url, "filled": selector, "value": value}
                raise ValueError(
                    f"PlaywrightTool: unknown tool_name '{tool_name}' "
                    f"(supported: navigate, screenshot, click, fill)"
                )
            finally:
                await browser.close()
