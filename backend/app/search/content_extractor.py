"""
AURA AI Content Extractor
Visits webpages via Playwright, extracts article content.
"""

import logging
from urllib.parse import urlparse

from playwright.async_api import Page, Browser

from app.search.content_cleaner import ContentCleaner

logger = logging.getLogger(__name__)


class ExtractedContent:
    """Holds extracted page content and metadata."""

    def __init__(
        self,
        url: str,
        title: str = "",
        content: str = "",
        description: str = "",
        source_domain: str = "",
        success: bool = True,
        error: str = "",
    ):
        self.url = url
        self.title = title
        self.content = content
        self.description = description
        self.source_domain = source_domain
        self.success = success
        self.error = error


class ContentExtractor:
    """
    Extracts clean article content from web pages using Playwright.

    Strategies (tried in order):
    1. <article> tag content
    2. <main> tag content
    3. Largest text block heuristic
    4. Full body fallback
    """

    def __init__(self, page_timeout: int = 10, max_content_length: int = 3000):
        self.page_timeout = page_timeout * 1000  # ms
        self.max_content_length = max_content_length
        self.cleaner = ContentCleaner(max_length=max_content_length)

    async def extract(self, page: Page, url: str) -> ExtractedContent:
        """
        Visit a URL and extract clean content.
        Uses existing Playwright page instance.
        """
        domain = urlparse(url).netloc.replace("www.", "")

        try:
            # Navigate to page
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.page_timeout,
            )

            if not response or response.status >= 400:
                status = response.status if response else "no response"
                return ExtractedContent(
                    url=url,
                    source_domain=domain,
                    success=False,
                    error=f"HTTP {status}",
                )

            # Wait a bit for dynamic content
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # Timeout OK — some pages never reach networkidle

            # Extract title
            title = await page.title() or ""

            # Extract meta description
            description = await self._get_meta_description(page)

            # Extract main content using multiple strategies
            content = await self._extract_content(page)

            if not content:
                return ExtractedContent(
                    url=url,
                    title=title,
                    description=description,
                    source_domain=domain,
                    success=False,
                    error="No content extracted",
                )

            return ExtractedContent(
                url=url,
                title=title,
                content=content,
                description=description,
                source_domain=domain,
                success=True,
            )

        except Exception as e:
            logger.warning(f"Content extraction failed for {url}: {e}")
            return ExtractedContent(
                url=url,
                source_domain=domain,
                success=False,
                error=str(e),
            )

    async def _extract_content(self, page: Page) -> str:
        """
        Try multiple extraction strategies in priority order.
        Returns cleaned text content.
        """
        # Strategy 1: <article> tag
        content = await self._try_selector(page, "article")
        if content and len(content) > 200:
            return content

        # Strategy 2: <main> tag
        content = await self._try_selector(page, "main")
        if content and len(content) > 200:
            return content

        # Strategy 3: Role=main
        content = await self._try_selector(page, "[role='main']")
        if content and len(content) > 200:
            return content

        # Strategy 4: Common content class patterns
        for selector in [
            ".post-content", ".article-content", ".entry-content",
            ".content-body", ".story-body", "#content", ".post-body",
            ".article-body", ".article__body",
        ]:
            content = await self._try_selector(page, selector)
            if content and len(content) > 200:
                return content

        # Strategy 5: Largest text block heuristic
        content = await self._largest_text_block(page)
        if content and len(content) > 100:
            return content

        # Strategy 6: Body fallback
        content = await self._try_selector(page, "body")
        return content or ""

    async def _try_selector(self, page: Page, selector: str) -> str | None:
        """Try to extract content from a CSS selector."""
        try:
            element = await page.query_selector(selector)
            if not element:
                return None
            html = await element.inner_html()
            return self.cleaner.clean(html)
        except Exception:
            return None

    async def _largest_text_block(self, page: Page) -> str | None:
        """Find the largest text-containing element."""
        try:
            # Get all paragraphs grouped by parent
            result = await page.evaluate("""
                () => {
                    const parents = new Map();
                    document.querySelectorAll('p, li, td').forEach(el => {
                        const parent = el.parentElement;
                        if (!parent) return;
                        const key = parent.tagName + '_' + 
                            Array.from(parent.parentElement?.children || []).indexOf(parent);
                        const current = parents.get(key) || { html: '', length: 0 };
                        current.html += el.outerHTML;
                        current.length += el.textContent.length;
                        parents.set(key, current);
                    });
                    
                    let best = { html: '', length: 0 };
                    for (const [, val] of parents) {
                        if (val.length > best.length) {
                            best = val;
                        }
                    }
                    return best.html;
                }
            """)

            if result and len(result) > 100:
                return self.cleaner.clean(result)
            return None

        except Exception:
            return None

    async def _get_meta_description(self, page: Page) -> str:
        """Extract meta description."""
        try:
            desc = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]') ||
                                 document.querySelector('meta[property="og:description"]');
                    return meta ? meta.getAttribute('content') : '';
                }
            """)
            return desc or ""
        except Exception:
            return ""
