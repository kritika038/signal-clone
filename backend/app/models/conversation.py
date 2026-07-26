import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Enum as SQLEnum, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.models.enums import ConversationType

class Conversation(Base):
    """
    Conversation represents a direct or group communication channel.
    """
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    type: Mapped[ConversationType] = mapped_column(
        SQLEnum(ConversationType),
        index=True,
        nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    last_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL", use_alter=True, name="fk_conv_last_msg"),
        nullable=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
        nullable=False
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Relationships
    members: Mapped[List["ConversationMember"]] = relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    preferences: Mapped[List["ConversationPreference"]] = relationship(
        "ConversationPreference",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="Message.conversation_id",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    typing_statuses: Mapped[List["TypingStatus"]] = relationship(
        "TypingStatus",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )

    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    updater: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by]
    )
    last_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        foreign_keys=[last_message_id],
        post_update=True
    )
