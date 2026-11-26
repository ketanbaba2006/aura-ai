"""
AURA AI Google Search Module
Searches Google via Playwright browser automation.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from playwright.async_api import Browser, BrowserContext, Page, async_playwright, Playwright

from app.config import settings

logger = logging.getLogger(__name__)

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


@dataclass
class SearchResult:
    """A single Google search result."""
    title: str = ""
    url: str = ""
    snippet: str = ""
    position: int = 0


class GoogleSearchModule:
    """
    Searches Google via Playwright browser automation.

    Features:
    - Headless Chromium browser
    - User-agent rotation
    - Random delays (anti-detection)
    - Consent page handling
    - CAPTCHA detection
    - Error recovery
    """

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Lazy-initialize Playwright and browser."""
        if self._initialized:
            return

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.SEARCH_HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            self._initialized = True
            logger.info("Google Search browser initialized (headless Chromium)")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def shutdown(self) -> None:
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False
        logger.info("Google Search browser shut down")

    async def _create_context(self) -> BrowserContext:
        """Create a new browser context with random user agent."""
        if not self._browser:
            await self.initialize()

        user_agent = random.choice(USER_AGENTS)
        context = await self._browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Block unnecessary resources for speed
        await context.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )
        await context.route(
            "**/{analytics,tracking,ads,advertisement}**",
            lambda route: route.abort(),
        )

        return context

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """
        Search Google and return results.

        Args:
            query: Search query string
            num_results: Maximum results to return

        Returns:
            List of SearchResult with title, URL, snippet
        """
        context = None
        page = None

        try:
            context = await self._create_context()
            page = await context.new_page()

            # Navigate to Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
            logger.info(f"Searching Google: {query}")

            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)

            # Handle consent page (GDPR)
            await self._handle_consent(page)

            # Random delay (anti-detection)
            await asyncio.sleep(random.uniform(1.0, 2.5))

            # Check for CAPTCHA
            if await self._is_captcha(page):
                logger.warning("Google CAPTCHA detected — aborting search")
                return []

            # Extract results
            results = await self._extract_results(page, num_results)

            logger.info(f"Found {len(results)} results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []

        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def _handle_consent(self, page: Page) -> None:
        """Handle Google consent/cookie page if it appears."""
        try:
            # Look for consent buttons (various localizations)
            for selector in [
                "button:has-text('Accept all')",
                "button:has-text('Accept')",
                "button:has-text('I agree')",
                "button:has-text('Agree')",
                "#L2AGLb",  # Google consent button ID
                "button[id='L2AGLb']",
            ]:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    logger.info("Handled Google consent page")
                    return
        except Exception:
            pass  # No consent page — continue

    async def _is_captcha(self, page: Page) -> bool:
        """Check if Google is showing a CAPTCHA."""
        try:
            content = await page.content()
            captcha_indicators = [
                "recaptcha", "captcha", "unusual traffic",
                "not a robot", "verify you're human",
            ]
            content_lower = content.lower()
            return any(indicator in content_lower for indicator in captcha_indicators)
        except Exception:
            return False

    async def _extract_results(
        self, page: Page, num_results: int
    ) -> list[SearchResult]:
        """Extract search results from Google results page."""
        results = []

        try:
            # Google search result selectors
            # Each result is in a div with class 'g' or similar structure
            result_elements = await page.evaluate("""
                (maxResults) => {
                    const results = [];
                    
                    // Primary selector: standard search results
                    const items = document.querySelectorAll('div.g, div[data-hveid] > div > div > div > a[href]');
                    const seen = new Set();
                    
                    // Try standard 'g' class results first
                    document.querySelectorAll('div.g').forEach(el => {
                        if (results.length >= maxResults) return;
                        
                        const linkEl = el.querySelector('a[href]');
                        const titleEl = el.querySelector('h3');
                        const snippetEl = el.querySelector('[data-sncf], .VwiC3b, [style*="-webkit-line-clamp"]');
                        
                        if (!linkEl || !titleEl) return;
                        
                        const url = linkEl.getAttribute('href');
                        if (!url || url.startsWith('/') || seen.has(url)) return;
                        if (url.includes('google.com/search')) return;
                        
                        seen.add(url);
                        results.push({
                            title: titleEl.textContent || '',
                            url: url,
                            snippet: snippetEl ? snippetEl.textContent || '' : '',
                        });
                    });
                    
                    // Fallback: broader selector if few results
                    if (results.length < 3) {
                        document.querySelectorAll('[data-header-feature] a[href], .yuRUbf a[href]').forEach(el => {
                            if (results.length >= maxResults) return;
                            
                            const url = el.getAttribute('href');
                            if (!url || url.startsWith('/') || seen.has(url)) return;
                            if (url.includes('google.com')) return;
                            
                            seen.add(url);
                            const titleEl = el.querySelector('h3') || el;
                            const parent = el.closest('div.g') || el.parentElement?.parentElement;
                            const snippetEl = parent?.querySelector('.VwiC3b, [data-sncf]');
                            
                            results.push({
                                title: titleEl.textContent || '',
                                url: url,
                                snippet: snippetEl ? snippetEl.textContent || '' : '',
                            });
                        });
                    }
                    
                    return results;
                }
            """, num_results)

            for i, item in enumerate(result_elements or []):
                if i >= num_results:
                    break

                url = item.get("url", "")
                # Filter out Google's own URLs and non-http
                if not url.startswith("http"):
                    continue

                results.append(
                    SearchResult(
                        title=item.get("title", "").strip(),
                        url=url,
                        snippet=item.get("snippet", "").strip(),
                        position=i + 1,
                    )
                )

        except Exception as e:
            logger.error(f"Result extraction failed: {e}")

        return results

    async def get_page_for_extraction(self) -> tuple[BrowserContext, Page]:
        """
        Get a new browser context + page for content extraction.
        Caller is responsible for closing.
        """
        context = await self._create_context()
        page = await context.new_page()
        return context, page
