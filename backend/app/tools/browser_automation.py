"""
AURA AI Browser Automation Tool
Allows the AI to browse the web using Playwright, extract text, take screenshots, and interact.
"""

import logging
from typing import Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.database.schemas import ToolResult
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BrowserAutomationTool(BaseTool):
    """
    Browser Automation Tool for interacting with web pages.
    """

    @property
    def name(self) -> str:
        return "browser_automation"

    @property
    def description(self) -> str:
        return (
            "Automate a headless web browser to interact with web pages. "
            "Supported actions: 'extract_text' (get page text content), 'html' (get raw HTML), "
            "'click' (click an element by selector), 'type' (type text into an element by selector). "
            "Use this for scraping dynamically rendered content or interacting with forms."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["extract_text", "html", "click", "type"],
                    "description": "The action to perform on the web page."
                },
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to before performing the action."
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the target element (required for click and type actions)."
                },
                "text": {
                    "type": "string",
                    "description": "Text to type into the element (required for type action)."
                }
            },
            "required": ["action", "url"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action")
        url = kwargs.get("url")
        selector = kwargs.get("selector")
        text = kwargs.get("text")

        if not action or not url:
            return ToolResult(success=False, error="Missing required parameters: 'action' and 'url'")

        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(headless=True)
                except Exception as e:
                    if "Executable doesn't exist" in str(e):
                        return ToolResult(success=False, error="Playwright browsers not installed. Please run 'playwright install chromium' on the backend.")
                    raise e
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # Set timeout to 15 seconds to avoid hanging too long
                page.set_default_timeout(15000)

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout while navigating to {url}, attempting to continue anyway.")
                except Exception as e:
                    await browser.close()
                    return ToolResult(success=False, error=f"Failed to navigate to URL: {e}")

                output_result = ""

                try:
                    if action == "extract_text":
                        # Wait a bit for JS to render
                        try:
                            await page.wait_for_load_state("networkidle", timeout=3000)
                        except:
                            pass
                        output_result = await page.evaluate("document.body.innerText")
                    
                    elif action == "html":
                        output_result = await page.content()
                        
                    elif action == "click":
                        if not selector:
                            raise ValueError("Selector is required for 'click' action")
                        await page.click(selector)
                        # Wait for potential navigation or rendering
                        try:
                            await page.wait_for_load_state("networkidle", timeout=3000)
                        except:
                            pass
                        output_result = f"Successfully clicked element: {selector}\nNew page URL: {page.url}"
                        
                    elif action == "type":
                        if not selector or not text:
                            raise ValueError("Selector and text are required for 'type' action")
                        await page.fill(selector, text)
                        output_result = f"Successfully typed text into element: {selector}"

                except Exception as e:
                    await browser.close()
                    return ToolResult(success=False, error=f"Failed to execute action '{action}': {e}")

                await browser.close()
                
                # Truncate output if it's excessively large (e.g., massive text dumps)
                if len(output_result) > 50000:
                    output_result = output_result[:50000] + "\n...[Output truncated due to length]..."

                return ToolResult(success=True, output=output_result)

        except Exception as e:
            logger.error(f"BrowserAutomationTool unexpected error: {e}")
            return ToolResult(success=False, error=f"Unexpected error: {str(e)}")
