"""PDF text extraction.

Returns text per page so that downstream chunks can carry an accurate page
number for citations.
"""

from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class ExtractedPage:
    page_number: int  # 1-based, matching what a reader sees
    text: str


def extract_pages(file_bytes: bytes) -> list[ExtractedPage]:
    """Extract text from each page of a PDF given as raw bytes."""
    pages: list[ExtractedPage] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for index, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages.append(ExtractedPage(page_number=index + 1, text=text))
    return pages
