"""Uploaded document model and its processing lifecycle."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="research", nullable=False)

    # Distinguishes documents within recruitment mode: "job" or "resume".
    # Research documents use the neutral default "document".
    role: Mapped[str] = mapped_column(String(20), default="document", nullable=False)

    # Lifecycle: pending -> processing -> ready -> failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
    chunks: Mapped[list["DocumentChunk"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
