import uuid
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class MessageReaction(Base):
    """
    MessageReaction stores user reactions on specific messages.
    """
    __tablename__ = "message_reactions"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reaction: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    unicode: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "reaction", name="uq_reactions_msg_user_react"),
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="reactions")
    user: Mapped["User"] = relationship("User", back_populates="reactions")
