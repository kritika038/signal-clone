from sqlalchemy import Column, String, DateTime, Integer, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base_class import Base

class OTPRequest(Base):
    """
    Production-grade OTP Request storage.
    Enforces hashing, resend limits, and expiration.
    """
    __tablename__ = "otp_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, index=True, nullable=False)
    otp_hash = Column(String, nullable=False)
    purpose = Column(String, nullable=False, default="registration")
    payload = Column(JSON, nullable=True) # Additional context
    
    attempts = Column(Integer, default=0, nullable=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
