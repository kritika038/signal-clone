import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.models.enums import PresenceStatus

class User(Base):
    """
    User entity representing a Signal user.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
        nullable=True
    )
    bio: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    presence_status: Mapped[PresenceStatus] = mapped_column(
        SQLEnum(PresenceStatus),
        default=PresenceStatus.OFFLINE,
        nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Relationships
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    # Social relationships
    contacts_owned: Mapped[List["Contact"]] = relationship(
        "Contact",
        foreign_keys="Contact.owner_id",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    contacts_of: Mapped[List["Contact"]] = relationship(
        "Contact",
        foreign_keys="Contact.contact_user_id",
        back_populates="contact_user",
        cascade="all, delete-orphan"
    )
    blocked_users: Mapped[List["BlockedUser"]] = relationship(
        "BlockedUser",
        foreign_keys="BlockedUser.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    blocked_by: Mapped[List["BlockedUser"]] = relationship(
        "BlockedUser",
        foreign_keys="BlockedUser.blocked_user_id",
        back_populates="blocked_user",
        cascade="all, delete-orphan"
    )
    memberships: Mapped[List["ConversationMember"]] = relationship(
        "ConversationMember",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    conversation_preferences: Mapped[List["ConversationPreference"]] = relationship(
        "ConversationPreference",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    messages_sent: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    receipts: Mapped[List["MessageReceipt"]] = relationship(
        "MessageReceipt",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    reactions: Mapped[List["MessageReaction"]] = relationship(
        "MessageReaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    device_tokens: Mapped[List["DeviceToken"]] = relationship(
        "DeviceToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

