import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.enums import MessageType, PresenceStatus, ReceiptStatus

class WSMessageSend(BaseModel):
    conversation_id: uuid.UUID
    content: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    reply_to_id: Optional[uuid.UUID] = None
    attachments: Optional[List[Dict[str, Any]]] = None

class WSMessageEdit(BaseModel):
    message_id: uuid.UUID
    content: str = Field(..., min_length=1)

class WSMessageDelete(BaseModel):
    message_id: uuid.UUID

class WSReceiptUpdate(BaseModel):
    message_id: uuid.UUID

class WSTypingEvent(BaseModel):
    conversation_id: uuid.UUID

class WSPresenceUpdate(BaseModel):
    status: PresenceStatus
