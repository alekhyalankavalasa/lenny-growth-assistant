"""
Artifact sanitization.
Defense-in-depth: server-side bleach + documented allowlist.
See architecture.md for full security rationale.

Allowed HTML tags and attributes:
  Structural: p, div, section, article, header, footer, main, aside, nav
  Headings:   h1, h2, h3, h4, h5, h6
  Lists:      ul, ol, li, dl, dt, dd
  Inline:     span, strong, em, b, i, u, s, del, ins, mark, small, sub, sup
  Code:       code, pre, kbd, samp, var
  Links:      a (href, title only — target forced to _blank, rel=noopener)
  Quotes:     blockquote, cite, q
  Tables:     table, thead, tbody, tfoot, tr, th, td, caption, colgroup, col
  Media:      (none — img, video, audio are blocked to prevent data exfil)
  Other:      br, hr

Blocked unconditionally:
  script, style, iframe, object, embed, form, input, button, select, textarea,
  link, meta, base, noscript, template, slot, canvas, svg, math
  All event attributes (onclick, onload, onerror, etc.)
  javascript: and data: URIs in href/src
"""
import re
import bleach
from bleach.css_sanitizer import CSSSanitizer

# ─── Allowlists ───────────────────────────────────────────────────────────────

ALLOWED_TAGS = [
    # Structure
    "p", "div", "section", "article", "header", "footer", "main", "aside", "nav",
    # Headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # Lists
    "ul", "ol", "li", "dl", "dt", "dd",
    # Inline
    "span", "strong", "em", "b", "i", "u", "s", "del", "ins", "mark", "small", "sub", "sup",
    # Code
    "code", "pre", "kbd", "samp", "var",
    # Links
    "a",
    # Quotes
    "blockquote", "cite", "q",
    # Tables
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col",
    # Misc
    "br", "hr",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "th": ["scope", "colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
    "blockquote": ["cite"],
    "code": ["class"],  # for syntax highlighting class names only
    "pre": ["class"],
}

# Block javascript: and data: URIs
def _clean_link(attrs, new=False):
    href = attrs.get((None, "href"), "")
    if href.lower().startswith(("javascript:", "data:", "vbscript:")):
        return None  # drop the attribute
    # Force safe external links
    attrs[(None, "target")] = "_blank"
    attrs[(None, "rel")] = "noopener noreferrer"
    return attrs


def sanitize_html(raw_html: str) -> str:
    """
    Sanitize HTML content for safe rendering in the Artifact Viewer.
    Strips all disallowed tags, event attributes, and dangerous URIs.
    """
    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,        # strip disallowed tags (not escape them)
        strip_comments=True,
    )
    # Apply link cleaner to handle javascript: hrefs that bleach may miss
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[_clean_link],
        skip_tags=["pre", "code"],
    )
    return cleaned


def sanitize_markdown_to_text(markdown: str) -> str:
    """
    For Markdown artifacts: return as-is (client renders via marked + DOMPurify).
    Light server-side check: block embedded HTML script tags.
    """
    # Remove any <script> blocks that might be in the markdown
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", markdown, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned
