import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.user_settings import UserSettings
from app.repositories.user import UserRepository
from app.repositories.settings import SettingsRepository
from app.schemas.auth import ProfileUpdate

class UserService:
    """
    UserService handles user queries and profile adjustments.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.settings_repo = SettingsRepository(db)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        query = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.settings))
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        query = (
            select(User)
            .where(User.phone == phone, User.deleted_at.is_(None))
            .options(selectinload(User.settings))
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        query = (
            select(User)
            .where(User.username == username, User.deleted_at.is_(None))
            .options(selectinload(User.settings))
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def update_profile(self, user_id: uuid.UUID, profile_in: ProfileUpdate) -> User:
        """
        Updates display details or settings columns atomically inside a single transaction.
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Update core user fields
        if profile_in.display_name is not None:
            user.display_name = profile_in.display_name
        if profile_in.bio is not None:
            user.bio = profile_in.bio
        if profile_in.avatar_url is not None:
            user.avatar_url = profile_in.avatar_url

        # Retrieve or initialize settings
        settings = user.settings
        if not settings:
            settings = UserSettings(user_id=user_id)
            self.db.add(settings)
            user.settings = settings

        # Update settings fields
        if profile_in.theme is not None:
            settings.theme = profile_in.theme
        if profile_in.language is not None:
            settings.language = profile_in.language
        if profile_in.privacy_last_seen is not None:
            settings.privacy_last_seen = profile_in.privacy_last_seen
        if profile_in.privacy_profile_photo is not None:
            settings.privacy_profile_photo = profile_in.privacy_profile_photo
        if profile_in.privacy_read_receipts is not None:
            settings.privacy_read_receipts = profile_in.privacy_read_receipts
        if profile_in.privacy_typing_indicator is not None:
            settings.privacy_typing_indicator = profile_in.privacy_typing_indicator
        if profile_in.notifications_enabled is not None:
            settings.notifications_enabled = profile_in.notifications_enabled
        if profile_in.auto_download_media is not None:
            settings.auto_download_media = profile_in.auto_download_media
        if profile_in.default_disappearing_timer is not None:
            settings.default_disappearing_timer = profile_in.default_disappearing_timer
        if profile_in.font_size is not None:
            settings.font_size = profile_in.font_size

        await self.db.commit()
        return await self.get_by_id(user_id)
