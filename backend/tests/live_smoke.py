"""Live smoke test against the real Gemini API.

Unlike the integration test (which uses a fake provider), this exercises the
genuine LLM round-trip: real embeddings, summary, citation-grounded chat,
structured extraction, and recruitment matching.

Requires:
  * GEMINI_API_KEY in backend/.env
  * the docker-compose `db` service running
  * sample PDFs fetched (scripts/fetch_samples.py)

Run from backend/:  python -m tests.live_smoke
"""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.llm import get_llm
from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.document import Document

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "chexnet.pdf"


def _section(title: str) -> None:
    print("\n" + "=" * 70 + f"\n{title}\n" + "-" * 70)


def main() -> None:
    _section("Embedding dimension check")
    vec = get_llm().embed(["hello world"])[0]
    print(f"embedding length = {len(vec)} (expected 768)")
    assert len(vec) == 768, "Embedding dimension does not match the vector column."

    Base.metadata.drop_all(bind=engine)
    init_db()
    client = TestClient(app)

    _section("Auth")
    reg = client.post(
        "/api/auth/register",
        json={"email": "live@example.com", "full_name": "Live Tester", "password": "password123"},
    )
    reg.raise_for_status()
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    user_id = reg.json()["user"]["id"]
    print("registered + authenticated")

    _section("Upload + background processing (real extraction/embeddings/summary)")
    if not SAMPLE.exists():
        raise SystemExit(f"Missing sample {SAMPLE}; run scripts/fetch_samples.py first.")
    with SAMPLE.open("rb") as fh:
        up = client.post(
            "/api/documents",
            headers=headers,
            files={"file": (SAMPLE.name, fh, "application/pdf")},
            data={"title": "CheXNet", "mode": "research", "role": "document"},
        )
    up.raise_for_status()
    doc_id = up.json()["id"]

    # Poll until processing finishes.
    status, doc = "pending", {}
    for _ in range(60):
        doc = client.get(f"/api/documents/{doc_id}", headers=headers).json()
        status = doc["status"]
        if status in ("ready", "failed"):
            break
        time.sleep(2)
    print(f"status = {status}, pages = {doc.get('page_count')}")
    if status == "failed":
        raise SystemExit(f"Processing failed: {doc.get('error')}")
    assert status == "ready"
    print(f"\nSummary:\n{doc['summary']}")

    _section("Citation-grounded chat")
    chat = client.post(
        f"/api/documents/{doc_id}/chat",
        headers=headers,
        json={"question": "What medical condition does the model detect?"},
    ).json()
    print(f"Answer:\n{chat['answer']}")
    print(f"\nCitations: {len(chat['citations'])}")
    for c in chat["citations"]:
        print(f"  [{c['marker']}] page {c['page_number']}: {c['snippet'][:90]}…")

    _section("Structured extraction (research schema)")
    extraction = client.get(f"/api/documents/{doc_id}/extraction", headers=headers).json()
    for key, value in extraction.items():
        print(f"  {key}: {value}")

    _section("Recruitment matching (real scoring)")
    job_id = _seed(user_id, "Backend Engineer", "job",
                   "We are hiring a backend engineer with strong Python, FastAPI and PostgreSQL experience.")
    strong = _seed(user_id, "Python Candidate", "resume",
                   "Senior software engineer, 6 years building Python and FastAPI services on PostgreSQL.")
    weak = _seed(user_id, "Designer Candidate", "resume",
                 "Graphic designer skilled in Photoshop and illustration, no programming experience.")

    match = client.post("/api/recruitment/match", headers=headers, json={"job_id": job_id}).json()
    print(f"Job: {match['job_title']} — ranked {len(match['results'])} candidate(s):")
    for r in match["results"]:
        print(f"  #{r['score']:>3}  {r['resume_title']:<20} "
              f"(semantic {r['semantic_score']}) matched={r['matched_skills']} missing={r['missing_skills']}")
        print(f"        {r['recommendation']}")

    assert match["results"][0]["resume_id"] == strong, "Stronger candidate should rank first"
    assert weak in {r["resume_id"] for r in match["results"]}

    print("\n" + "=" * 70 + "\nLIVE SMOKE TEST PASSED\n" + "=" * 70)


def _seed(owner_id: int, title: str, role: str, text: str) -> int:
    """Insert a ready recruitment document with one real-embedded chunk."""
    db = SessionLocal()
    doc = Document(
        owner_id=owner_id, title=title, filename=f"{title}.pdf",
        mode="recruitment", role=role, status="ready", page_count=1,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.add(DocumentChunk(
        document_id=doc.id, chunk_index=0, page_number=1,
        content=text, embedding=get_llm().embed([text])[0],
    ))
    db.commit()
    new_id = doc.id
    db.close()
    return new_id


if __name__ == "__main__":
    main()
