import uuid
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Attachment(Base):
    """
    Attachment stores metadata for media or file files linked to messages.
    """
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    storage_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    width: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    height: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    duration: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="attachments")
