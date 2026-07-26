import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterSchema(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=255, description="Unique identifier for the device")
    platform: str = Field(..., min_length=1, max_length=50, description="Platform identifier (ios, android, web)")
    fcm_token: str = Field(..., min_length=1, max_length=512, description="Firebase Cloud Messaging token")


class DeviceResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    device_id: str
    platform: str
    fcm_token: str
    created_at: datetime
    updated_at: datetime
    last_seen: datetime
