import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class BlockedUser(Base):
    """
    BlockedUser maps a blocking user to a blocked user.
    """
    __tablename__ = "blocked_users"

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
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "blocked_user_id", name="uq_blocked_users_user_blocked"),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="blocked_users"
    )
    blocked_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[blocked_user_id],
        back_populates="blocked_by"
    )
