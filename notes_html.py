"""Shared HTML-notes walker used by both the DOCX and PDF exporters. Mirrors the
node-walking algorithm of NotesWordExporter.java (appendHtml/appendBlock/appendRuns)
so both export formats stay behaviorally identical."""
from dataclasses import dataclass, field
from typing import List, Union

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class TextRun:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class LineBreak:
    pass


Run = Union[TextRun, LineBreak]


@dataclass
class Block:
    kind: str  # "title1" | "title2" | "title3" | "bullet" | "paragraph"
    text: str = ""             # plain text, for title1/title2/title3 (headings drop inline formatting,
                                # matching el.text() in the Java version)
    runs: List[Run] = field(default_factory=list)  # for bullet/paragraph


def parse_blocks(html: str) -> List[Block]:
    if not html or not html.strip():
        return []
    soup = BeautifulSoup(html, "html.parser")
    blocks: List[Block] = []
    for node in soup.contents:
        blocks.extend(_blocks_for_node(node))
    return blocks


def _blocks_for_node(node) -> List[Block]:
    if isinstance(node, NavigableString):
        text = str(node)
        if text.strip():
            return [Block(kind="paragraph", runs=[TextRun(text=text)])]
        return []
    if not isinstance(node, Tag):
        return []

    tag = node.name
    if tag == "h1":
        return [Block(kind="title1", text=node.get_text())]
    if tag == "h2":
        return [Block(kind="title2", text=node.get_text())]
    if tag == "h3":
        return [Block(kind="title3", text=node.get_text())]
    if tag == "ul":
        return [Block(kind="bullet", runs=_runs_for(li, False, False, False))
                for li in node.find_all("li", recursive=False)]
    return [Block(kind="paragraph", runs=_runs_for(node, False, False, False))]


def _runs_for(container, bold: bool, italic: bool, underline: bool) -> List[Run]:
    runs: List[Run] = []
    for node in container.contents:
        if isinstance(node, NavigableString):
            text = str(node)
            if text != "":
                runs.append(TextRun(text=text, bold=bold, italic=italic, underline=underline))
        elif isinstance(node, Tag):
            if node.name == "br":
                runs.append(LineBreak())
                continue
            child_bold = bold or node.name in ("b", "strong")
            child_italic = italic or node.name in ("i", "em")
            child_underline = underline or node.name == "u"
            runs.extend(_runs_for(node, child_bold, child_italic, child_underline))
    return runs
