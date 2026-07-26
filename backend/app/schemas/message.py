from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class MessageBase(BaseModel):
    recipient_id: UUID = Field(..., description="UUID of the chat recipient")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content body")
    message_type: str = Field(default="text", max_length=20)

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_id: UUID
    is_read: bool
    created_at: datetime
    updated_at: datetime
