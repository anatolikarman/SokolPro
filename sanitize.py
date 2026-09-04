"""Notes HTML sanitization mirroring Jsoup's Safelist.basic() + h1/h2/h3, as used
by ClientController#sanitizeNotes in the original Java app."""
from typing import Optional

import bleach
from bs4 import BeautifulSoup

ALLOWED_TAGS = [
    "a", "b", "blockquote", "br", "cite", "code", "dd", "dl", "dt", "em",
    "i", "li", "ol", "p", "pre", "q", "small", "span", "strike", "strong", "sub",
    "sup", "u", "ul", "h1", "h2", "h3",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href"],
    "blockquote": ["cite"],
    "q": ["cite"],
}

ALLOWED_PROTOCOLS = ["ftp", "http", "https", "mailto"]


def sanitize_notes(notes: Optional[str]) -> Optional[str]:
    if notes is None:
        return None

    # Jsoup's Safelist-based cleaner drops "data" tags such as <script>/<style>
    # entirely, including their raw text content, rather than unwrapping them.
    # bleach's strip=True only removes the tag markup and keeps the inner text,
    # which would leak script/style bodies as visible text -- so drop those
    # subtrees ourselves first to match Jsoup's behavior.
    pre = BeautifulSoup(notes, "html.parser")
    for tag in pre(["script", "style"]):
        tag.decompose()
    notes = str(pre)

    cleaned = bleach.clean(
        notes,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    # A contenteditable box left empty by the user often still submits stray markup
    # (e.g. "<br>" or "<p></p>") rather than an empty string, so check the visible
    # text rather than the raw HTML to decide whether there's actually content.
    visible_text = BeautifulSoup(cleaned, "html.parser").get_text()
    return None if visible_text.strip() == "" else cleaned
