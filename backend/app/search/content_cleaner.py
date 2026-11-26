"""
AURA AI Content Cleaner
Strips ads, navigation, clutter from HTML. Returns clean text.
"""

import re
import logging
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Tags to completely remove (including content)
REMOVE_TAGS = {
    "script", "style", "noscript", "iframe", "svg", "canvas",
    "form", "input", "button", "select", "textarea",
    "nav", "footer", "header", "aside",
    "figure", "figcaption", "picture", "video", "audio",
    "dialog", "menu", "menuitem",
}

# Tags that are ad/clutter indicators (remove if they have these classes/ids)
CLUTTER_PATTERNS = [
    r"ad[-_]?", r"advertisement", r"banner", r"sidebar",
    r"popup", r"modal", r"overlay", r"cookie",
    r"social[-_]?share", r"share[-_]?button", r"related[-_]?post",
    r"comment", r"newsletter", r"subscribe", r"promo",
    r"sponsored", r"widget", r"breadcrumb", r"pagination",
    r"footer", r"header", r"nav", r"menu",
]

CLUTTER_RE = re.compile("|".join(CLUTTER_PATTERNS), re.IGNORECASE)

# Block-level tags (add newlines)
BLOCK_TAGS = {
    "p", "div", "section", "article", "main",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre",
    "table", "tr", "td", "th",
    "br", "hr",
}

# Heading tags for markdown conversion
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class CleanTextExtractor(HTMLParser):
    """
    HTML parser that extracts clean text content.
    Strips all tags, keeps text, respects block-level structure.
    """

    def __init__(self):
        super().__init__()
        self.result: list[str] = []
        self.skip_depth = 0
        self.current_tag_stack: list[str] = []
        self._in_heading = False
        self._heading_level = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()

        # Skip entire subtree for removed tags
        if tag in REMOVE_TAGS:
            self.skip_depth += 1
            return

        if self.skip_depth > 0:
            return

        # Check for clutter by class/id
        attr_dict = dict(attrs)
        class_val = attr_dict.get("class", "") or ""
        id_val = attr_dict.get("id", "") or ""
        combined = f"{class_val} {id_val}"

        if CLUTTER_RE.search(combined):
            self.skip_depth += 1
            return

        # Track tag stack
        self.current_tag_stack.append(tag)

        # Add newlines for block elements
        if tag in BLOCK_TAGS:
            self.result.append("\n")

        # Track headings
        if tag in HEADING_TAGS:
            self._in_heading = True
            self._heading_level = int(tag[1])
            prefix = "#" * self._heading_level + " "
            self.result.append(f"\n{prefix}")

        # List items
        if tag == "li":
            self.result.append("• ")

        # Links — skip tag but keep text
        if tag == "a":
            pass  # text handled by handle_data

        # Line break
        if tag == "br":
            self.result.append("\n")

    def handle_endtag(self, tag: str):
        tag = tag.lower()

        if tag in REMOVE_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return

        if self.skip_depth > 0:
            # Could be closing a clutter tag
            if CLUTTER_RE.search(tag):
                self.skip_depth = max(0, self.skip_depth - 1)
            return

        if self.current_tag_stack and self.current_tag_stack[-1] == tag:
            self.current_tag_stack.pop()

        if tag in BLOCK_TAGS:
            self.result.append("\n")

        if tag in HEADING_TAGS:
            self._in_heading = False
            self.result.append("\n")

    def handle_data(self, data: str):
        if self.skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.result.append(text + " ")

    def get_text(self) -> str:
        return "".join(self.result)


class ContentCleaner:
    """
    Cleans raw HTML content into readable text.
    Removes ads, navigation, scripts, clutter.
    """

    def __init__(self, max_length: int = 3000):
        self.max_length = max_length

    def clean(self, html: str) -> str:
        """Clean HTML and return plain text."""
        if not html:
            return ""

        try:
            # Phase 1: Parse HTML and extract text
            extractor = CleanTextExtractor()
            extractor.feed(html)
            text = extractor.get_text()

            # Phase 2: Post-process text
            text = self._post_process(text)

            # Phase 3: Truncate
            if len(text) > self.max_length:
                text = self._smart_truncate(text, self.max_length)

            return text.strip()

        except Exception as e:
            logger.error(f"Content cleaning failed: {e}")
            # Fallback: crude regex strip
            return self._fallback_clean(html)

    def _post_process(self, text: str) -> str:
        """Clean up extracted text."""
        # Collapse multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multiple spaces
        text = re.sub(r"[ \t]{2,}", " ", text)
        # Remove lines that are just whitespace
        lines = [line.rstrip() for line in text.split("\n")]
        # Remove very short lines (likely navigation remnants)
        lines = [
            line for line in lines
            if len(line.strip()) > 2 or line.strip() == ""
        ]
        # Remove duplicate consecutive lines
        deduped = []
        for line in lines:
            if not deduped or line != deduped[-1]:
                deduped.append(line)

        return "\n".join(deduped)

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Truncate at sentence boundary."""
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]
        # Try to break at sentence end
        for sep in [". ", ".\n", "! ", "? ", "\n\n"]:
            last = truncated.rfind(sep)
            if last > max_length * 0.7:
                return truncated[: last + 1].rstrip() + "\n\n[Content truncated]"

        # Break at word boundary
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:
            return truncated[:last_space] + "...\n\n[Content truncated]"

        return truncated + "...\n\n[Content truncated]"

    def _fallback_clean(self, html: str) -> str:
        """Crude fallback: regex-strip all tags."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text[: self.max_length].strip()
