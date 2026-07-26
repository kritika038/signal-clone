import uuid
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Notification(Base):
    """
    Notification tracks alerts delivered to users for new messages or reactions.
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    type: Mapped[str] = mapped_column(
        String(50),
        default="MESSAGE",  # MESSAGE, REACTION, MISSED_CALL, SYSTEM
        nullable=False
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    message: Mapped[Optional["Message"]] = relationship("Message", back_populates="notifications")
