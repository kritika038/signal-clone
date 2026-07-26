import uuid
from sqlalchemy import ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class ConversationDraft(Base):
    """
    ConversationDraft stores unsent message drafts per conversation/user.
    """
    __tablename__ = "conversation_drafts"

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
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_drafts_conv_user"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation")
    user: Mapped["User"] = relationship("User")
