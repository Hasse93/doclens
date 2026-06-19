"""Build reports for a document (summary, extraction, notes) as Markdown or PDF."""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.note import Note
from app.services import extraction_service


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- _None_"]


def build_markdown_report(db: Session, document: Document) -> str:
    lines: list[str] = [f"# {document.title}", ""]
    lines.append(f"*Source file: {document.filename} · {document.page_count} pages*")
    lines.append("")

    if document.summary:
        lines += ["## Summary", "", document.summary, ""]

    lines += ["## Structured data", ""]
    if document.mode == "recruitment":
        data = extraction_service.extract_recruitment_fields(db, document.id)
        lines += [
            f"- **Name:** {data.name or '—'}",
            f"- **Email:** {data.email or '—'}",
            f"- **Current title:** {data.current_title or '—'}",
            f"- **Years of experience:** {data.years_experience if data.years_experience is not None else '—'}",
            "",
            "**Skills**",
            *_bullets(data.skills),
            "",
            "**Education**",
            *_bullets(data.education),
            "",
        ]
    else:
        data = extraction_service.extract_research_fields(db, document.id)
        lines += [
            f"- **Title:** {data.title or '—'}",
            f"- **Authors:** {', '.join(data.authors) if data.authors else '—'}",
            f"- **Methodology:** {data.methodology or '—'}",
            f"- **Dataset:** {data.dataset or '—'}",
            f"- **Limitations:** {data.limitations or '—'}",
            "",
            "**Key findings**",
            *_bullets(data.key_findings),
            "",
        ]

    notes = db.execute(
        select(Note).where(Note.document_id == document.id).order_by(Note.created_at)
    ).scalars().all()
    lines += ["## Notes", ""]
    if notes:
        for note in notes:
            stamp = note.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"- _{stamp}_ — {note.content}")
    else:
        lines.append("_No notes._")
    lines.append("")

    return "\n".join(lines)


# Map characters outside the core-font (latin-1) range to safe equivalents.
_UNICODE_FIXUPS = {
    "—": "-", "–": "-", "…": "...",
    "‘": "'", "’": "'", "“": '"', "”": '"', "•": "-",
}


def _ascii_safe(text: str) -> str:
    for bad, good in _UNICODE_FIXUPS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf_report(db: Session, document: Document) -> bytes:
    """Render the Markdown report to a simple, clean PDF."""
    markdown = build_markdown_report(db, document)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def write(height: float, text: str) -> None:
        # new_x/new_y return the cursor to the left margin on the next line,
        # which multi_cell does not do by default.
        pdf.multi_cell(0, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    for raw in markdown.split("\n"):
        line = _ascii_safe(raw.rstrip())
        if not line:
            pdf.ln(3)
            continue

        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            write(9, line[2:])
            pdf.ln(1)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            write(8, line[3:])
        elif line.startswith("- "):
            pdf.set_font("Helvetica", "", 11)
            write(6, f"  - {_strip_emphasis(line[2:])}")
        elif line.startswith("**") and line.endswith("**"):
            pdf.set_font("Helvetica", "B", 11)
            write(6, line.strip("*"))
        elif line.startswith("*") and line.endswith("*"):
            pdf.set_font("Helvetica", "I", 9)
            write(6, line.strip("*"))
        else:
            pdf.set_font("Helvetica", "", 11)
            write(6, _strip_emphasis(line))

    return bytes(pdf.output())


def _strip_emphasis(text: str) -> str:
    return text.replace("**", "").replace("_", "")
