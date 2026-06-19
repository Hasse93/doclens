"""Retrieval and answer-quality evaluation for DocLens.

For each labelled question this measures two things:

  * retrieval hit-rate  — did the retrieved passages contain the expected
    information? (a proxy for "did we fetch the right chunks?")
  * answer accuracy      — did the generated answer contain the expected
    information? (a proxy for faithfulness end-to-end)

The harness ingests the sample PDFs in memory (extract -> chunk -> embed) and
ranks chunks by cosine similarity, mirroring the production retriever without
needing a database. It uses the configured LLM provider, so a real run needs
GEMINI_API_KEY. Pass --fake for a no-key smoke test of the harness itself.

Usage (from backend/, with samples fetched):
    python -m eval.run_eval
    python -m eval.run_eval --fake     # mechanics only, metrics not meaningful
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.core.llm.base import LLMProvider
from app.core.rag.chunker import chunk_pages
from app.core.rag.extractor import extract_pages
from app.core.rag.prompts import build_qa_prompt, RESEARCH_SYSTEM

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"


@dataclass
class IndexedChunk:
    page_number: int
    content: str
    vector: list[float]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def build_index(llm: LLMProvider, pdf_path: Path, pace: float = 0.0) -> list[IndexedChunk]:
    chunks = chunk_pages(extract_pages(pdf_path.read_bytes()))
    # Embed one chunk per call when pacing, so a whole paper does not exceed the
    # free-tier per-minute token limit in a single large request.
    indexed: list[IndexedChunk] = []
    for chunk in chunks:
        vector = llm.embed([chunk.content])[0]
        indexed.append(IndexedChunk(chunk.page_number, chunk.content, vector))
        if pace:
            time.sleep(pace)
    return indexed


def retrieve(llm: LLMProvider, index: list[IndexedChunk], question: str, k: int) -> list[IndexedChunk]:
    q = llm.embed_query(question)
    ranked = sorted(index, key=lambda ch: _cosine(q, ch.vector), reverse=True)
    return ranked[:k]


def _hit(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate DocLens retrieval and answers.")
    parser.add_argument("--fake", action="store_true", help="Use a fake LLM (no API key).")
    parser.add_argument("--top-k", type=int, default=settings.retrieval_top_k)
    parser.add_argument(
        "--pace",
        type=float,
        default=0.0,
        help="Seconds to pause between API calls, to stay under free-tier rate limits.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Limit evaluation to these sample filenames (default: all in the dataset).",
    )
    args = parser.parse_args()
    pace = 0.0 if args.fake else args.pace

    llm = _FakeLLM() if args.fake else _real_llm()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = dataset["cases"]
    if args.files:
        wanted = set(args.files)
        cases = [c for c in cases if c["file"] in wanted]

    # Build one index per referenced file (reused across that file's questions).
    indexes: dict[str, list[IndexedChunk]] = {}
    for filename in {c["file"] for c in cases}:
        pdf = SAMPLES_DIR / filename
        if not pdf.exists():
            print(f"Missing sample: {pdf}. Run scripts/fetch_samples.py first.")
            return 1
        indexes[filename] = build_index(llm, pdf, pace)
        if pace:
            time.sleep(pace)

    retrieval_hits = 0
    answer_hits = 0
    print(f"\nEvaluating {len(cases)} cases (top_k={args.top_k})\n" + "-" * 72)

    for case in cases:
        index = indexes[case["file"]]
        passages = retrieve(llm, index, case["question"], args.top_k)

        retrieved_text = " ".join(p.content for p in passages)
        retrieval_ok = _hit(retrieved_text, case["expected_keywords"])

        answer = llm.generate(
            build_qa_prompt(case["question"], [p.content for p in passages]),
            system=RESEARCH_SYSTEM,
        )
        answer_ok = _hit(answer, case["expected_keywords"])

        retrieval_hits += retrieval_ok
        answer_hits += answer_ok
        flag = "OK " if retrieval_ok else "MISS"
        print(f"[{flag}] {case['file']:<30} {case['question'][:34]:<34} "
              f"retr={'Y' if retrieval_ok else 'n'} ans={'Y' if answer_ok else 'n'}")
        if pace:
            time.sleep(pace)

    n = len(cases)
    print("-" * 72)
    print(f"Retrieval hit-rate : {retrieval_hits}/{n}  ({retrieval_hits / n:.0%})")
    print(f"Answer accuracy    : {answer_hits}/{n}  ({answer_hits / n:.0%})")
    return 0


def _real_llm() -> LLMProvider:
    from app.core.llm import get_llm

    return get_llm()


class _FakeLLM(LLMProvider):
    """Deterministic stand-in so the harness can be smoke-tested without a key."""

    def _vec(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text.lower())
        return [(seed % 101) / 101.0] * 32

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def generate(self, prompt: str, system: str | None = None) -> str:
        return "Answer derived from the retrieved passages."


if __name__ == "__main__":
    raise SystemExit(main())
