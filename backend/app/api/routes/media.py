import re
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_async_db, get_session_manager
from app.implementations.db_session_manager import DBSessionManager
from app.services.runtime import runtime_services
from app.models.user import User
from app.models.message import Message
from app.models.attachment import Attachment
from app.models.conversation_member import ConversationMember
from app.core.exceptions import APIException

router = APIRouter(prefix="/conversations", tags=["Media Gallery"])
upload_router = APIRouter(prefix="/media", tags=["Media Upload"])

async def _validate_membership(conversation_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    query = select(ConversationMember).where(
        and_(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
            ConversationMember.left_at.is_(None)
        )
    )
    res = await db.execute(query)
    if not res.scalar_one_or_none():
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "User is not a member of this conversation")

@router.get("/{id}/media", response_model=Dict[str, Any])
async def get_conversation_media(
    id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Returns paginated images, videos, and media files shared in a conversation.
    """
    await _validate_membership(id, current_user.id, db)
    
    # Query attachments where mime_type starts with image or video
    query = (
        select(Attachment)
        .join(Message, Message.id == Attachment.message_id)
        .where(
            and_(
                Message.conversation_id == id,
                Message.deleted_at.is_(None),
                or_(
                    Attachment.mime_type.ilike("image/%"),
                    Attachment.mime_type.ilike("video/%")
                )
            )
        )
        .order_by(Attachment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(query)
    attachments = res.scalars().all()
    
    media_list = []
    for att in attachments:
        media_list.append({
            "id": str(att.id),
            "message_id": str(att.message_id),
            "original_filename": att.original_filename,
            "mime_type": att.mime_type,
            "size": att.size,
            "thumbnail_url": att.thumbnail_url,
            "playback_url": att.playback_url if hasattr(att, "playback_url") else f"/api/v1/attachments/download/{att.storage_key}"
        })
        
    return {
        "success": True,
        "data": {
            "media": media_list,
            "skip": skip,
            "limit": limit
        }
    }

@router.get("/{id}/files", response_model=Dict[str, Any])
async def get_conversation_files(
    id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Returns paginated document files (PDFs, docs, text files) shared in a conversation.
    """
    await _validate_membership(id, current_user.id, db)
    
    query = (
        select(Attachment)
        .join(Message, Message.id == Attachment.message_id)
        .where(
            and_(
                Message.conversation_id == id,
                Message.deleted_at.is_(None),
                Attachment.mime_type.not_like("image/%"),
                Attachment.mime_type.not_like("video/%"),
                Attachment.mime_type.not_like("audio/%")
            )
        )
        .order_by(Attachment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(query)
    attachments = res.scalars().all()
    
    files_list = []
    for att in attachments:
        files_list.append({
            "id": str(att.id),
            "message_id": str(att.message_id),
            "original_filename": att.original_filename,
            "mime_type": att.mime_type,
            "size": att.size,
            "playback_url": f"/api/v1/attachments/download/{att.storage_key}"
        })
        
    return {
        "success": True,
        "data": {
            "files": files_list,
            "skip": skip,
            "limit": limit
        }
    }

@router.get("/{id}/links", response_model=Dict[str, Any])
async def get_conversation_links(
    id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Scans conversation message text history for shared URLs and returns them.
    """
    await _validate_membership(id, current_user.id, db)
    
    # Query text messages that contain http:// or https://
    query = (
        select(Message)
        .where(
            and_(
                Message.conversation_id == id,
                Message.deleted_at.is_(None),
                Message.content.ilike("%http%")
            )
        )
        .order_by(Message.created_at.desc())
    )
    res = await db.execute(query)
    messages = res.scalars().all()
    
    links = []
    url_pattern = re.compile(r'(https?://[^\s]+)')
    
    for msg in messages:
        content = msg.content
        if not content:
            continue
        matches = url_pattern.findall(content)
        for url in matches:
            links.append({
                "message_id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "url": url,
                "created_at": msg.created_at.isoformat()
            })
            
    # Apply pagination manually on extracted list
    paginated_links = links[skip:skip + limit]
    
    return {
        "success": True,
        "data": {
            "links": paginated_links,
            "skip": skip,
            "limit": limit,
            "total_count": len(links)
        }
    }


@upload_router.post("/upload", response_model=Dict[str, Any])
async def upload_media(
    file: UploadFile = File(...),
    authorization: Optional[str] = Depends(APIKeyHeader(name="Authorization", auto_error=False)),
    db: AsyncSession = Depends(get_async_db),
    session_manager: DBSessionManager = Depends(get_session_manager),
):
    # Try to authenticate, but allow anonymous (for avatar upload during registration)
    current_user_id = None
    if authorization:
        token = authorization[7:] if authorization.lower().startswith("bearer ") else authorization
        try:
            from app.core.config import settings
            from jose import jwt
            import uuid
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            current_user_id = uuid.UUID(payload["sub"])
        except Exception:
            pass

    if not file.filename or not file.content_type:
        raise APIException(status.HTTP_400_BAD_REQUEST, "INVALID_FILE", "Uploaded file is missing metadata")

    try:
        file_bytes = await file.read()
        upload = await runtime_services.storage_provider.upload_file(
            file_bytes=file_bytes,
            filename=file.filename,
            mime_type=file.content_type,
        )
    except Exception as e:
        import traceback
        import logging
        logging.getLogger("uvicorn").error(f"Upload failed: {traceback.format_exc()}")
        raise APIException(status.HTTP_400_BAD_REQUEST, "UPLOAD_FAILED", f"Upload failed: {str(e)}")

    return {
        "success": True,
        "data": {
            **upload,
            "uploaded_by": str(current_user_id) if current_user_id else None,
        },
    }
