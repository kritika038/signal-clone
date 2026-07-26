import uuid
from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class TypingStatus(Base):
    """
    TypingStatus serves purely as an audit/logging entity.
    Not used during live websocket operations to prevent DB performance bottlenecks.
    """
    __tablename__ = "typing_statuses"

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
    is_typing: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="typing_statuses")
    user: Mapped["User"] = relationship("User")
Base.metadata
