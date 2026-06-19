"""Splitting extracted pages into overlapping, page-attributed chunks.

Chunking is word-based with a sliding window. The overlap keeps sentences that
straddle a boundary retrievable from either chunk, which noticeably improves
answer quality on long paragraphs.
"""

from dataclasses import dataclass

from app.config import settings
from app.core.rag.extractor import ExtractedPage


@dataclass
class Chunk:
    chunk_index: int
    page_number: int
    content: str


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    step = max(size - overlap, 1)
    pieces: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + size]
        if window:
            pieces.append(" ".join(window))
        if start + size >= len(words):
            break
    return pieces


def chunk_pages(pages: list[ExtractedPage]) -> list[Chunk]:
    """Produce a flat, globally indexed list of chunks across all pages."""
    size = settings.chunk_size
    overlap = settings.chunk_overlap

    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        for piece in _split_text(page.text, size, overlap):
            chunks.append(Chunk(chunk_index=index, page_number=page.page_number, content=piece))
            index += 1
    return chunks
