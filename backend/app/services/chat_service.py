"""Citation-grounded question answering over documents.

Conversations are persisted: each question and its grounded answer (with
citations) are stored so the chat history survives a page reload. A streaming
variant emits the answer token-by-token over Server-Sent Events.
"""

import json
import re
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.llm import get_llm
from app.core.rag.prompts import build_qa_prompt, RESEARCH_SYSTEM
from app.core.rag.retriever import retrieve, retrieve_multi
from app.models.chat_message import ChatMessage
from app.schemas.chat import (
    ChatResponse,
    Citation,
    MultiChatResponse,
    MultiCitation,
)

_SNIPPET_CHARS = 240


def _snippet(content: str) -> str:
    snippet = content[:_SNIPPET_CHARS].rstrip()
    return snippet + "…" if len(content) > _SNIPPET_CHARS else snippet


def _persist_turn(
    db: Session,
    document_id: int,
    owner_id: int,
    question: str,
    answer: str,
    citations: list[Citation],
) -> None:
    db.add(ChatMessage(owner_id=owner_id, document_id=document_id, role="user", content=question))
    db.add(
        ChatMessage(
            owner_id=owner_id,
            document_id=document_id,
            role="assistant",
            content=answer,
            citations=[c.model_dump() for c in citations],
        )
    )
    db.commit()


def answer_question(
    db: Session, document_id: int, owner_id: int, question: str
) -> ChatResponse:
    passages = retrieve(db, document_id, question)
    if not passages:
        answer = "I couldn't find anything relevant to that question in this document."
        _persist_turn(db, document_id, owner_id, question, answer, [])
        return ChatResponse(answer=answer, citations=[])

    prompt = build_qa_prompt(question, [p.content for p in passages])
    answer = get_llm().generate(prompt, system=RESEARCH_SYSTEM)
    citations = _citations_for(answer, passages)
    _persist_turn(db, document_id, owner_id, question, answer, citations)
    return ChatResponse(answer=answer, citations=citations)


def stream_answer(
    db: Session, document_id: int, owner_id: int, question: str
) -> Iterator[str]:
    """Yield Server-Sent Events: many `token` events, then one `done` event.

    The full answer is accumulated, citations resolved, and the turn persisted
    once streaming finishes.
    """
    passages = retrieve(db, document_id, question)
    if not passages:
        answer = "I couldn't find anything relevant to that question in this document."
        yield _sse("token", {"text": answer})
        _persist_turn(db, document_id, owner_id, question, answer, [])
        yield _sse("done", {"citations": []})
        return

    prompt = build_qa_prompt(question, [p.content for p in passages])
    parts: list[str] = []
    for piece in get_llm().generate_stream(prompt, system=RESEARCH_SYSTEM):
        parts.append(piece)
        yield _sse("token", {"text": piece})

    answer = "".join(parts).strip()
    citations = _citations_for(answer, passages)
    _persist_turn(db, document_id, owner_id, question, answer, citations)
    yield _sse("done", {"citations": [c.model_dump() for c in citations]})


def history(db: Session, document_id: int) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.document_id == document_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    )
    return list(db.execute(stmt).scalars().all())


def clear_history(db: Session, document_id: int) -> None:
    for message in history(db, document_id):
        db.delete(message)
    db.commit()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _citations_for(answer: str, passages) -> list[Citation]:
    """Return citations for the passage markers the model actually used.

    The model is asked to cite passages as [1], [2], ... matching the order in
    which they were supplied. We surface only the markers it referenced.
    """
    used = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    citations: list[Citation] = []
    for index, passage in enumerate(passages, start=1):
        if index in used:
            citations.append(
                Citation(
                    marker=index,
                    page_number=passage.page_number,
                    snippet=_snippet(passage.content),
                )
            )
    return citations


def answer_across_documents(
    db: Session, document_ids: list[int], question: str
) -> MultiChatResponse:
    passages = retrieve_multi(db, document_ids, question)
    if not passages:
        return MultiChatResponse(
            answer="I couldn't find anything relevant to that question in the selected documents.",
            citations=[],
        )

    prompt = build_qa_prompt(question, [p.content for p in passages])
    answer = get_llm().generate(prompt, system=RESEARCH_SYSTEM)

    used = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    citations = [
        MultiCitation(
            marker=index,
            document_id=passage.document_id,
            document_title=passage.document_title,
            page_number=passage.page_number,
            snippet=_snippet(passage.content),
        )
        for index, passage in enumerate(passages, start=1)
        if index in used
    ]
    return MultiChatResponse(answer=answer, citations=citations)
