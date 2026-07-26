import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class ConversationPreference(Base):
    """
    ConversationPreference stores user-specific visual and notification overrides for a chat.
    """
    __tablename__ = "conversation_preferences"

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
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_muted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    mute_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    wallpaper: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    custom_notification: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    notification_sound: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    disappearing_timer: Mapped[int] = mapped_column(
        Integer,
        default=0,  # 0 indicates disabled
        nullable=False
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_prefs_conv_user"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="preferences")
    user: Mapped["User"] = relationship("User", back_populates="conversation_preferences")
