from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.interfaces.otp_store import OTPStore
from app.models.otp import OTPRequest
from app.core.security import get_password_hash, verify_password

class DatabaseOTPStore(OTPStore):
    """
    Production-grade OTP Store backed by the database.
    Enforces rate limits (30s resend, max 5 attempts/hour) and hashes OTPs.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, identifier: str, registration_payload: Dict[str, Any], otp: str, ttl_seconds: int = 300) -> None:
        """
        Create a new OTP request or update an existing one.
        identifier could be a phone number, email, or registration token.
        """
        now = datetime.now(timezone.utc)
        
        # Rate Limiting: Max 5 OTPs per hour for this identifier
        # (This applies to the OTPs generated in the last hour)
        # Note: Since we overwrite the row, we need a separate log to track counts perfectly, 
        # but for simplicity, we can just track if we hit 5 attempts on the current record.
        # Wait, if we overwrite the record, we lose the previous history for the hourly limit.
        # But the prompt says "max 5 OTP/hour". 
        # If we just use the `attempts` column for verifications, we need another way for generation count, or we don't overwrite but insert multiple?
        # The prompt instructed to use `otp_requests` table with `id, email, otp_hash, purpose, expires_at, attempts, created_at, updated_at`.
        # Wait! The user's columns: `id, email, otp_hash, purpose, expires_at, attempts, created_at, updated_at`. 
        # I used `email` as unique? No, I used `identifier` as unique? Ah, the user said:
        # "2. Use a dedicated otp_requests table. Columns: id, email, otp_hash, purpose, expires_at, attempts, created_at, updated_at"
        # Since they didn't specify `email` as unique, we can insert MULTIPLE rows per email!
        # This makes tracking 5 OTPs/hour easy. We just count rows in the last hour!
        
        # Let's count how many OTPs generated in the last hour
        one_hour_ago = now - timedelta(hours=1)
        result = await self.db.execute(
            select(func.count(OTPRequest.id)).where(
                OTPRequest.email == identifier,
                OTPRequest.created_at >= one_hour_ago
            )
        )
        count_last_hour = result.scalar() or 0
        if count_last_hour >= 5:
            raise ValueError("Too many verification codes requested. Please try again later.")

        # Check for 30s resend limit
        result = await self.db.execute(
            select(OTPRequest).where(
                OTPRequest.email == identifier
            ).order_by(OTPRequest.created_at.desc()).limit(1)
        )
        last_request = result.scalar_one_or_none()
        
        if last_request and (now - last_request.created_at).total_seconds() < 30:
            raise ValueError("Please wait 30 seconds before requesting a new code.")

        # Invalidate old OTPs for this email to ensure single active OTP?
        # Or we can just let them expire. The user said "OTP is single-use", and usually that means only the latest one is valid.
        # We can delete or update old ones, but deleting is cleaner.
        # Wait, if we delete them, we lose the history for the 1-hour rate limit!
        # Instead, we just mark the new one as the active one, or verify the most recent one.
        
        hashed = get_password_hash(otp)
        
        new_otp = OTPRequest(
            email=identifier,
            otp_hash=hashed,
            purpose="registration",
            payload=registration_payload,
            expires_at=now + timedelta(seconds=ttl_seconds),
            attempts=0
        )
        self.db.add(new_otp)
        await self.db.flush()

    async def verify(self, identifier: str, otp: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        
        # Get the most recent OTP request for this identifier
        result = await self.db.execute(
            select(OTPRequest).where(
                OTPRequest.email == identifier
            ).order_by(OTPRequest.created_at.desc()).limit(1)
        )
        req = result.scalar_one_or_none()
        
        if not req:
            return None
            
        if now > req.expires_at:
            return None
            
        if req.attempts >= 5:
            return None
            
        req.attempts += 1
        
        if not verify_password(otp, req.otp_hash):
            await self.db.flush()
            return None
            
        # Success - Single Use: delete the record
        payload = req.payload
        await self.db.delete(req)
        await self.db.flush()
        
        return payload

    async def delete(self, identifier: str) -> None:
        result = await self.db.execute(
            select(OTPRequest).where(OTPRequest.email == identifier)
        )
        requests = result.scalars().all()
        for req in requests:
            await self.db.delete(req)
        await self.db.flush()

    async def cleanup_expired(self) -> None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(OTPRequest).where(OTPRequest.expires_at < now)
        )
        requests = result.scalars().all()
        for req in requests:
            await self.db.delete(req)
        await self.db.flush()
