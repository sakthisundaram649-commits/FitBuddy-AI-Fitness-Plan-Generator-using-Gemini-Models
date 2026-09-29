"""
formatting.py
Converts the simple Markdown used by the workout plans and nutrition tips
(headings with # / ##, **bold**, * bullet lists, --- dividers) into safe,
clean HTML for display - so people see real bold text and bullet points
instead of literal *, #, and ** characters.
"""

import html
import re

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _inline(text: str) -> str:
    """Escape text for HTML, then turn **bold** into <strong>bold</strong>."""
    escaped = html.escape(text)
    return _BOLD_RE.sub(r"<strong>\1</strong>", escaped)


def markdown_to_html(text: str) -> str:
    """Convert a Markdown-ish plan/tip string into a block of HTML."""
    if not text:
        return ""

    lines = text.replace("\r\n", "\n").split("\n")
    html_parts = []
    list_items = []

    def flush_list():
        if list_items:
            html_parts.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            flush_list()
            continue

        if line in ("---", "***", "___"):
            flush_list()
            html_parts.append("<hr>")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            flush_list()
            level = min(len(heading_match.group(1)) + 2, 6)  # ## -> h4, keeps sizes modest
            html_parts.append(f"<h{level}>{_inline(heading_match.group(2))}</h{level}>")
            continue

        bullet_match = re.match(r"^[\*\-]\s+(.*)$", line)
        if bullet_match:
            list_items.append(_inline(bullet_match.group(1)))
            continue

        flush_list()
        # A whole line wrapped in ** ** (e.g. "**Day 1: ...**") reads better as a heading
        whole_bold = re.match(r"^\*\*(.+)\*\*:?$", line)
        if whole_bold:
            html_parts.append(f"<h4>{_inline(whole_bold.group(1))}</h4>")
        else:
            html_parts.append(f"<p>{_inline(line)}</p>")

    flush_list()
    return "\n".join(html_parts)
