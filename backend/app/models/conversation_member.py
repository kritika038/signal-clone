import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Enum as SQLEnum, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.models.enums import ConversationRole

class ConversationMember(Base):
    """
    ConversationMember tracks the participation of a user in a conversation.
    """
    __tablename__ = "conversation_members"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[ConversationRole] = mapped_column(
        SQLEnum(ConversationRole),
        default=ConversationRole.MEMBER,
        nullable=False
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    last_read_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL", use_alter=True, name="fk_member_last_read"),
        nullable=True
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_members_conv_user"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    last_read_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        foreign_keys=[last_read_message_id]
    )
