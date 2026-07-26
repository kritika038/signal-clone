from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

class Base(DeclarativeBase):
    """
    Base class for all database models.
    Automatically generates table names from class names.
    Includes standard audit timestamps for creation, update, and soft deletion.
    """
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Standard audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True
    )
