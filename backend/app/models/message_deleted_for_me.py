import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class MessageDeletedForMe(Base):
    """
    MessageDeletedForMe tracks users who have hidden a message from their own view (Delete For Me).
    """
    __tablename__ = "messages_deleted_for_me"

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
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "message_id", name="uq_msg_deleted_for_me_user_msg"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    message: Mapped["Message"] = relationship("Message")
