"""Download a few open-access papers from arXiv for demoing Research mode.

These PDFs are only sample inputs for the app — DocLens does not train on them.
They are downloaded into ./samples (which is gitignored) so the repository
stays free of large binaries. Re-running skips files that already exist.

Usage (from the project root):
    python scripts/fetch_samples.py
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

# (output filename, arXiv id, short reason it's a useful demo)
SAMPLES: list[tuple[str, str, str]] = [
    ("attention-is-all-you-need.pdf", "1706.03762", "The Transformer paper — a clear, well-known method/results structure."),
    ("bert.pdf", "1810.04805", "BERT — good for questions about pre-training and datasets."),
    ("resnet.pdf", "1512.03385", "Deep residual learning — concise methodology and benchmarks."),
    ("chexnet.pdf", "1711.05225", "CheXNet — a health-tech (radiology) paper to match the portfolio theme."),
]

ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
USER_AGENT = "DocLens-sample-fetcher/1.0 (portfolio demo)"


def fetch(arxiv_id: str, destination: Path) -> None:
    request = urllib.request.Request(
        ARXIV_PDF_URL.format(arxiv_id=arxiv_id), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def main() -> int:
    samples_dir = Path(__file__).resolve().parent.parent / "samples"
    samples_dir.mkdir(exist_ok=True)

    failures = 0
    for filename, arxiv_id, reason in SAMPLES:
        target = samples_dir / filename
        if target.exists():
            print(f"  skip  {filename} (already downloaded)")
            continue

        print(f"  get   {filename}  <- arXiv:{arxiv_id}")
        try:
            fetch(arxiv_id, target)
            print(f"        {target.stat().st_size // 1024} KB — {reason}")
        except (urllib.error.URLError, TimeoutError) as exc:
            failures += 1
            print(f"        failed: {exc}", file=sys.stderr)

    print(f"\nDone. Samples are in: {samples_dir}")
    if failures:
        print(f"{failures} download(s) failed — re-run to retry.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
