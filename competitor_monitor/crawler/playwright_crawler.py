from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from competitor_monitor.config import settings

logger = logging.getLogger(__name__)

# Rotate through common desktop user-agents to reduce bot detection
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


@dataclass
class CrawlResult:
    url: str
    html: str
    html_hash: str
    screenshot_path: str | None = None
    status_code: int = 200
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class PlaywrightCrawler:
    """
    Async crawler using Playwright (Chromium).

    Handles JavaScript-heavy sites by waiting for network idle before
    capturing HTML. Supports optional proxy rotation and screenshot capture.
    """

    def __init__(self, screenshot_dir: str | None = None) -> None:
        self._screenshot_dir = Path(screenshot_dir) if screenshot_dir else None
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> PlaywrightCrawler:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.playwright_headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _make_context(self, proxy_url: str | None = None) -> BrowserContext:
        proxy = {"server": proxy_url} if proxy_url else None
        context = await self._browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            locale="de-DE",
            timezone_id="Europe/Berlin",
            viewport={"width": 1440, "height": 900},
            proxy=proxy,
            extra_http_headers={
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        # Mask automation fingerprints
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return context

    async def crawl(
        self,
        url: str,
        *,
        take_screenshot: bool = False,
        wait_for_selector: str | None = None,
    ) -> CrawlResult:
        proxies = settings.proxy_list or [None]
        last_error: str | None = None

        for attempt in range(settings.crawler_max_retries):
            proxy = proxies[attempt % len(proxies)]
            try:
                result = await self._crawl_once(
                    url,
                    proxy_url=proxy,
                    take_screenshot=take_screenshot,
                    wait_for_selector=wait_for_selector,
                )
                if result.success:
                    return result
                last_error = result.error
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Crawl attempt %d/%d failed for %s: %s", attempt + 1, settings.crawler_max_retries, url, exc)

            backoff = 2 ** attempt
            await asyncio.sleep(backoff)

        return CrawlResult(
            url=url,
            html="",
            html_hash="",
            error=last_error or "Max retries exceeded",
        )

    async def _crawl_once(
        self,
        url: str,
        *,
        proxy_url: str | None,
        take_screenshot: bool,
        wait_for_selector: str | None,
    ) -> CrawlResult:
        context = await self._make_context(proxy_url)
        page: Page = await context.new_page()
        screenshot_path: str | None = None

        try:
            response = await page.goto(
                url,
                timeout=settings.crawler_timeout_ms,
                wait_until="networkidle",
            )
            status = response.status if response else 0

            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=10_000)

            # Small random delay to mimic human reading
            await asyncio.sleep(random.uniform(1.0, 2.5))

            html = await page.content()
            html_hash = hashlib.sha256(html.encode()).hexdigest()

            if take_screenshot and self._screenshot_dir:
                self._screenshot_dir.mkdir(parents=True, exist_ok=True)
                safe_name = url.replace("://", "_").replace("/", "_")[:100]
                path = self._screenshot_dir / f"{safe_name}.png"
                await page.screenshot(path=str(path), full_page=True)
                screenshot_path = str(path)

            return CrawlResult(
                url=url,
                html=html,
                html_hash=html_hash,
                screenshot_path=screenshot_path,
                status_code=status,
            )

        except Exception as exc:
            return CrawlResult(url=url, html="", html_hash="", error=str(exc))

        finally:
            await page.close()
            await context.close()
