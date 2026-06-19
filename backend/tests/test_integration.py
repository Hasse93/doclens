"""End-to-end integration test against a live pgvector database.

Runs the real FastAPI app and database. The LLM provider is replaced with a
deterministic fake so the test needs no API key and stays reproducible.

Run from backend/ with the docker-compose `db` service up:
    pytest -q   (or)   python -m tests.test_integration
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://doclens:doclens@localhost:5432/doclens"
)
os.environ.setdefault("GEMINI_API_KEY", "not-used-by-fake")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.llm.base import LLMProvider  # noqa: E402


class FakeLLM(LLMProvider):
    """Deterministic provider: stable embeddings and canned text."""

    def _vector(self, text: str) -> list[float]:
        # A simple, deterministic embedding: spread a hash across the dimensions
        # so similar strings land near each other and queries can match.
        seed = sum(ord(c) for c in text.lower())
        base = [(seed % 97) / 97.0] * 768
        if "method" in text.lower():
            base[0] += 0.5
        if "result" in text.lower():
            base[1] += 0.5
        return base

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def generate(self, prompt: str, system: str | None = None) -> str:
        system = system or ""
        if "overall_score" in prompt:
            # Score on the résumé portion only, so the JD's wording doesn't leak
            # in. Candidates mentioning python rank higher.
            resume_part = prompt.split("Candidate résumé:", 1)[-1]
            score = 88 if "python" in resume_part.lower() else 55
            return (
                f'{{"overall_score": {score}, "matched_skills": ["Python"], '
                '"missing_skills": ["Kubernetes"], "summary": "Solid fit overall."}'
            )
        if "résumé" in system or "resume" in prompt.lower() and "skills" in prompt.lower():
            return '{"name": "Jane Roe", "skills": ["Python"], "years_experience": 5}'
        if "academic" in system or "key_findings" in prompt:
            return '{"title": "A Study", "authors": ["Doe"], "key_findings": ["It works"]}'
        if "Summarise" in prompt:
            return "This document presents a method and reports positive results."
        return "The method is described on page 1 [1]."


def main() -> None:
    import app.core.llm as llm_module

    llm_module.get_llm.cache_clear()
    llm_module.get_llm = lambda: FakeLLM()  # type: ignore[assignment]

    # Patch the already-imported references in the service modules.
    from app.services import chat_service, document_service, extraction_service
    from app.core.rag import retriever

    fake = FakeLLM()
    for module in (chat_service, document_service, extraction_service, retriever):
        module.get_llm = lambda: fake  # type: ignore[attr-defined]

    from app.main import app
    from app.database import Base, SessionLocal, engine, init_db
    from app.models.document import Document
    from app.models.chunk import DocumentChunk

    # Start from a clean schema so the test is repeatable.
    Base.metadata.drop_all(bind=engine)
    init_db()
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}

    # Register and authenticate.
    reg = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "full_name": "Tester", "password": "password123"},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate registration is rejected.
    dup = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "full_name": "X", "password": "password123"},
    )
    assert dup.status_code == 409

    # Auth is enforced.
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/auth/me", headers=headers).json()["email"] == "tester@example.com"

    # Seed a fully processed document directly (mirrors what the background task
    # produces) so retrieval and chat can be exercised without file I/O.
    db = SessionLocal()
    user_id = reg.json()["user"]["id"]
    doc = Document(
        owner_id=user_id,
        title="A Study",
        filename="study.pdf",
        mode="research",
        status="ready",
        page_count=2,
        summary="A short summary.",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    passages = [
        ("The method uses a transformer trained on public data.", 1),
        ("The results show a clear improvement over the baseline.", 2),
    ]
    for i, (text, page) in enumerate(passages):
        db.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                page_number=page,
                content=text,
                embedding=fake.embed([text])[0],
            )
        )
    db.commit()
    doc_id = doc.id
    db.close()

    # Listing returns the document.
    listing = client.get("/api/documents", headers=headers)
    assert listing.status_code == 200 and len(listing.json()) == 1

    # Chat returns an answer with at least one citation carrying a page number.
    chat = client.post(
        f"/api/documents/{doc_id}/chat",
        headers=headers,
        json={"question": "What method is used?"},
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["answer"]
    assert body["citations"] and body["citations"][0]["page_number"] in (1, 2)

    # The turn is persisted: one user message + one assistant message.
    msgs = client.get(f"/api/documents/{doc_id}/messages", headers=headers).json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant"
    assert msgs[1]["citations"]

    # Streaming endpoint emits SSE token events then a done event with citations.
    stream = client.post(
        f"/api/documents/{doc_id}/chat/stream",
        headers=headers,
        json={"question": "What method is used?"},
    )
    assert stream.status_code == 200
    assert "event: token" in stream.text and "event: done" in stream.text

    # Streaming also persisted its turn (now 4 messages); clearing wipes them.
    assert len(client.get(f"/api/documents/{doc_id}/messages", headers=headers).json()) == 4
    assert client.delete(f"/api/documents/{doc_id}/messages", headers=headers).status_code == 204
    assert len(client.get(f"/api/documents/{doc_id}/messages", headers=headers).json()) == 0

    # Structured extraction validates against the schema.
    extraction = client.get(f"/api/documents/{doc_id}/extraction", headers=headers)
    assert extraction.status_code == 200, extraction.text
    assert extraction.json()["title"] == "A Study"
    assert extraction.json()["authors"] == ["Doe"]

    # --- Notes: create, list, include in report, delete ---------------------
    note = client.post(
        f"/api/documents/{doc_id}/notes",
        headers=headers,
        json={"content": "Revisit the evaluation section."},
    )
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]
    assert len(client.get(f"/api/documents/{doc_id}/notes", headers=headers).json()) == 1

    # --- Report export: Markdown with summary, extraction, and notes --------
    report = client.get(f"/api/documents/{doc_id}/report", headers=headers)
    assert report.status_code == 200, report.text
    assert "attachment" in report.headers.get("content-disposition", "")
    body = report.text
    assert "# A Study" in body
    assert "## Summary" in body
    assert "Revisit the evaluation section." in body

    # PDF export returns a real PDF document.
    pdf = client.get(f"/api/documents/{doc_id}/report?format=pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"

    assert client.delete(
        f"/api/documents/{doc_id}/notes/{note_id}", headers=headers
    ).status_code == 204
    assert len(client.get(f"/api/documents/{doc_id}/notes", headers=headers).json()) == 0

    # --- Multi-document Q&A: search across the user's research documents -----
    ask = client.post(
        "/api/documents/ask",
        headers=headers,
        json={"question": "What method is used?"},
    )
    assert ask.status_code == 200, ask.text
    ask_body = ask.json()
    assert ask_body["answer"]
    assert ask_body["citations"]
    assert ask_body["citations"][0]["document_title"] == "A Study"

    # Explicit document scoping works too.
    scoped = client.post(
        "/api/documents/ask",
        headers=headers,
        json={"question": "What method is used?", "document_ids": [doc_id]},
    )
    assert scoped.status_code == 200

    # --- Recruitment mode: rank résumés against a job description -----------
    def seed_doc(title: str, role: str, passages: list[str]) -> int:
        s = SessionLocal()
        d = Document(
            owner_id=user_id,
            title=title,
            filename=f"{title}.pdf",
            mode="recruitment",
            role=role,
            status="ready",
            page_count=1,
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        for i, text in enumerate(passages):
            s.add(
                DocumentChunk(
                    document_id=d.id,
                    chunk_index=i,
                    page_number=1,
                    content=text,
                    embedding=fake.embed([text])[0],
                )
            )
        s.commit()
        new_id = d.id
        s.close()
        return new_id

    job_doc_id = seed_doc("Backend Engineer", "job", ["We need a Python backend engineer."])
    strong_id = seed_doc("Strong CV", "resume", ["Senior Python developer, 5 years."])
    weak_id = seed_doc("Weak CV", "resume", ["Graphic designer with no programming."])

    match = client.post(
        "/api/recruitment/match", headers=headers, json={"job_id": job_doc_id}
    )
    assert match.status_code == 200, match.text
    ranked = match.json()["results"]
    assert len(ranked) == 2
    # Results come back sorted by score, strongest first.
    assert ranked[0]["score"] >= ranked[1]["score"]
    assert ranked[0]["resume_id"] == strong_id
    assert "Python" in ranked[0]["matched_skills"]

    # Re-running replaces prior results rather than duplicating them.
    again = client.post(
        "/api/recruitment/match", headers=headers, json={"job_id": job_doc_id}
    ).json()
    assert len(again["results"]) == 2

    # Recruitment extraction returns the résumé schema on a recruitment document.
    resume_fields = client.get(f"/api/documents/{strong_id}/extraction", headers=headers).json()
    assert "skills" in resume_fields and resume_fields["skills"] == ["Python"]

    # Matching another user's job is rejected.
    other_match = client.post(
        "/api/recruitment/match",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_id": 999999},
    )
    assert other_match.status_code == 400

    # Ownership is enforced: a second user cannot see the first user's document.
    other = client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "full_name": "Other", "password": "password123"},
    ).json()["access_token"]
    forbidden = client.get(
        f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {other}"}
    )
    assert forbidden.status_code == 404

    # Delete cleans up: the research document is gone, recruitment docs remain.
    assert client.delete(f"/api/documents/{doc_id}", headers=headers).status_code == 204
    remaining = {d["id"] for d in client.get("/api/documents", headers=headers).json()}
    assert doc_id not in remaining
    assert {job_doc_id, strong_id, weak_id} <= remaining

    print("INTEGRATION TEST PASSED")


if __name__ == "__main__":
    main()
