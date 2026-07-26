import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Enum as SQLEnum, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.models.enums import MessageType

class Message(Base):
    """
    Message represents a chat message sent within a conversation.
    """
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    message_type: Mapped[MessageType] = mapped_column(
        SQLEnum(MessageType),
        default=MessageType.TEXT,
        nullable=False
    )
    reply_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    forwarded_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Extended Columns for Advanced Messaging Features
    client_message_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    is_draft: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_messages_conv_created", "conversation_id", "created_at"),
        Index("idx_messages_created", "created_at"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        back_populates="messages"
    )
    sender: Mapped["User"] = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="messages_sent"
    )
    forwarded_from: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[forwarded_from_id]
    )
    parent_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        remote_side=[id],
        back_populates="replies"
    )
    replies: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="parent_message"
    )
    receipts: Mapped[List["MessageReceipt"]] = relationship(
        "MessageReceipt",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    reactions: Mapped[List["MessageReaction"]] = relationship(
        "MessageReaction",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="message",
        cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="message",
        cascade="all, delete-orphan"
    )
