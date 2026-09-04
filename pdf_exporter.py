"""PDF export mirroring notes-document-pdf.html's visual structure (title, subtitle,
a ruled heading per session date, and the sanitized notes body), built directly with
ReportLab Platypus. Shares the same HTML-notes walker as the DOCX exporter so both
export formats stay behaviorally identical.

(A full HTML->PDF pipeline, closer to the original openhtmltopdf-based renderer, was
tried via xhtml2pdf first, but it mishandles non-Latin1 text with a custom embedded
TTF font -- Cyrillic came out as replacement-glyph boxes even with correct UTF-8 input
and a directly-registered ReportLab font. Building the layout with Platypus keeps full
control over Unicode text and reuses the exact registered font that renders correctly.)
"""
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import List
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from models import Client, Session
from notes_html import Block, LineBreak, Run, TextRun, parse_blocks

FONT_DIR = Path(__file__).resolve().parent / "static" / "fonts"
FONT_NAME = "PdfFont"
FONT_NAME_BOLD = "PdfFont-Bold"

PX_TO_PT = 0.75  # CSS px are defined at 96dpi; PDF points are 72dpi.

_fonts_lock = Lock()
_fonts_registered = False


def _px(value: float) -> float:
    return value * PX_TO_PT


def _ensure_fonts_registered() -> None:
    global _fonts_registered
    if _fonts_registered:
        return
    with _fonts_lock:
        if _fonts_registered:
            return
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        # Only two weights ship with the app (regular/bold), same as the Java version's
        # openhtmltopdf font registration, so italic/bold-italic fall back to those.
        pdfmetrics.registerFontFamily(FONT_NAME, normal=FONT_NAME, bold=FONT_NAME_BOLD,
                                       italic=FONT_NAME, boldItalic=FONT_NAME_BOLD)
        _fonts_registered = True


def _styles():
    body = ParagraphStyle("body", fontName=FONT_NAME, fontSize=_px(16), leading=_px(16) * 1.5)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=_px(30), bulletIndent=_px(14))
    title1 = ParagraphStyle("notes-h1", fontName=FONT_NAME_BOLD, fontSize=_px(32),
                             leading=_px(32) * 1.2, spaceBefore=_px(12), spaceAfter=_px(6))
    title2 = ParagraphStyle("notes-h2", fontName=FONT_NAME_BOLD, fontSize=_px(24),
                             leading=_px(24) * 1.2, spaceBefore=_px(12), spaceAfter=_px(6))
    title3 = ParagraphStyle("notes-h3", fontName=FONT_NAME_BOLD, fontSize=_px(18.72),
                             leading=_px(18.72) * 1.2, spaceBefore=_px(12), spaceAfter=_px(6))
    doc_title = ParagraphStyle("doc-title", fontName=FONT_NAME_BOLD, fontSize=_px(22),
                                leading=_px(22) * 1.2, spaceAfter=_px(4))
    doc_subtitle = ParagraphStyle("doc-subtitle", fontName=FONT_NAME, fontSize=_px(16),
                                   leading=_px(16) * 1.5, textColor=colors.HexColor("#777777"),
                                   spaceAfter=_px(32))
    empty = ParagraphStyle("empty", fontName=FONT_NAME, fontSize=_px(16),
                            textColor=colors.HexColor("#777777"))
    session_h1 = ParagraphStyle("session-h1", fontName=FONT_NAME_BOLD, fontSize=_px(20),
                                 leading=_px(20) * 1.2, spaceAfter=_px(8))
    return {
        "body": body, "bullet": bullet, "title1": title1, "title2": title2, "title3": title3,
        "doc_title": doc_title, "doc_subtitle": doc_subtitle, "empty": empty, "session_h1": session_h1,
    }


def build(client: Client, sessions: List[Session]) -> bytes:
    _ensure_fonts_registered()
    styles = _styles()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=_px(40), rightMargin=_px(40), topMargin=_px(40), bottomMargin=_px(40),
        title=f"Заметки — {client.name}",
    )

    story = [
        Paragraph(xml_escape(f"Заметки клиента: {client.name}"), styles["doc_title"]),
        Paragraph("Все сеансы с заметками, от старых к новым", styles["doc_subtitle"]),
    ]

    has_backstory = bool(client.backstory and client.backstory.strip())
    if not has_backstory and not sessions:
        story.append(Paragraph("Заметок нет", styles["empty"]))

    first_h1 = True
    if has_backstory:
        _append_notes(story, client.backstory, styles)
        story.append(Spacer(1, _px(8)))
        _append_session_heading(story, "Конец предыстории", first_h1, styles)
        first_h1 = False

    for session in sessions:
        _append_session_heading(story, session.formatted_date, first_h1, styles)
        first_h1 = False
        _append_notes(story, session.notes, styles)
        story.append(Spacer(1, _px(8)))

    doc.build(story)
    return buf.getvalue()


def _append_session_heading(story: list, text: str, first: bool, styles: dict) -> None:
    style = styles["session_h1"]
    style.spaceBefore = 0 if first else _px(32)
    story.append(Paragraph(xml_escape(text), style))
    story.append(HRFlowable(width="100%", thickness=_px(2), color=colors.HexColor("#dddddd"),
                             spaceAfter=_px(12)))


def _append_notes(story: list, html: str, styles: dict) -> None:
    for block in parse_blocks(html):
        _append_block(story, block, styles)


def _append_block(story: list, block: Block, styles: dict) -> None:
    if block.kind == "title1":
        story.append(Paragraph(xml_escape(block.text), styles["title1"]))
    elif block.kind == "title2":
        story.append(Paragraph(xml_escape(block.text), styles["title2"]))
    elif block.kind == "title3":
        story.append(Paragraph(xml_escape(block.text), styles["title3"]))
    elif block.kind == "bullet":
        markup = _runs_to_markup(block.runs)
        story.append(Paragraph(f"•&nbsp;&nbsp;{markup}", styles["bullet"]))
    else:
        markup = _runs_to_markup(block.runs)
        if markup:
            story.append(Paragraph(markup, styles["body"]))


def _runs_to_markup(runs: List[Run]) -> str:
    parts = []
    for run in runs:
        if isinstance(run, LineBreak):
            parts.append("<br/>")
        elif isinstance(run, TextRun):
            text = xml_escape(run.text)
            if run.bold:
                text = f"<b>{text}</b>"
            if run.italic:
                text = f"<i>{text}</i>"
            if run.underline:
                text = f"<u>{text}</u>"
            parts.append(text)
    return "".join(parts)
