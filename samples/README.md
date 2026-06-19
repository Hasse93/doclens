# Sample documents

These are **demo inputs** for trying out DocLens — not training data. DocLens is
a retrieval system; it does not train on anything. See the main
[README](../README.md) for how the pipeline works.

The PDFs themselves are **not committed** (they are gitignored). Fetch them with:

```bash
python scripts/fetch_samples.py
```

The script downloads a small set of open-access papers from
[arXiv](https://arxiv.org), which permits redistribution of these PDFs:

| File | arXiv | Why it's a good demo |
| ---- | ----- | -------------------- |
| `attention-is-all-you-need.pdf` | [1706.03762](https://arxiv.org/abs/1706.03762) | The Transformer paper — clear method/results to question. |
| `bert.pdf` | [1810.04805](https://arxiv.org/abs/1810.04805) | Good for questions about pre-training and datasets. |
| `resnet.pdf` | [1512.03385](https://arxiv.org/abs/1512.03385) | Concise methodology and benchmark tables. |
| `chexnet.pdf` | [1711.05225](https://arxiv.org/abs/1711.05225) | A health-tech (radiology) paper matching the portfolio theme. |

Once downloaded, upload any of them in the app to see summaries,
citation-grounded Q&A, and structured extraction.

> For **Recruitment mode** (Phase 2) we will generate *synthetic* résumés and job
> descriptions rather than use real ones, to avoid handling personal data.
