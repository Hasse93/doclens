"""Chat (question-answering) schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    marker: int  # the [n] used in the answer text
    page_number: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list[Citation] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MultiChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # When omitted, every ready research document the user owns is searched.
    document_ids: list[int] | None = None


class MultiCitation(BaseModel):
    marker: int
    document_id: int
    document_title: str
    page_number: int
    snippet: str


class MultiChatResponse(BaseModel):
    answer: str
    citations: list[MultiCitation]
