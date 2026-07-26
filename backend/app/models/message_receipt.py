import uuid
from sqlalchemy import Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.models.enums import ReceiptStatus

class MessageReceipt(Base):
    """
    MessageReceipt tracks the delivery/read lifecycle of a message for a specific recipient.
    """
    __tablename__ = "message_receipts"

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
    status: Mapped[ReceiptStatus] = mapped_column(
        SQLEnum(ReceiptStatus),
        default=ReceiptStatus.SENDING,
        nullable=False
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_receipts_msg_user"),
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="receipts")
    user: Mapped["User"] = relationship("User", back_populates="receipts")
