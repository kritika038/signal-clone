import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class DeviceToken(Base):
    """
    DeviceToken tracks FCM push tokens associated with user devices.
    """
    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_device_tokens_user_device"),
        UniqueConstraint("fcm_token", name="uq_device_tokens_fcm_token"),
    )

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
    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    fcm_token: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="device_tokens")
