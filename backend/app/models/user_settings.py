import uuid
from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class UserSettings(Base):
    """
    UserSettings defines personalization and privacy parameters for a user.
    """
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    theme: Mapped[str] = mapped_column(
        String(20),
        default="dark",
        nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False
    )
    privacy_last_seen: Mapped[str] = mapped_column(
        String(20),
        default="EVERYBODY",  # EVERYBODY, CONTACTS, NOBODY
        nullable=False
    )
    privacy_profile_photo: Mapped[str] = mapped_column(
        String(20),
        default="EVERYBODY",  # EVERYBODY, CONTACTS, NOBODY
        nullable=False
    )
    privacy_read_receipts: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    privacy_typing_indicator: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    auto_download_media: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    default_disappearing_timer: Mapped[int] = mapped_column(
        Integer,
        default=0,  # 0 indicates disabled
        nullable=False
    )
    font_size: Mapped[str] = mapped_column(
        String(10),
        default="medium",
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")
