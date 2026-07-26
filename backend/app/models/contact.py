import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Contact(Base):
    """
    Contact matches one user to another under a localized nickname.
    """
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    contact_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("owner_id", "contact_user_id", name="uq_contacts_owner_contact"),
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="contacts_owned"
    )
    contact_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[contact_user_id],
        back_populates="contacts_of"
    )
