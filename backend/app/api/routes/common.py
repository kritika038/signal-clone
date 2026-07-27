from __future__ import annotations

from typing import Any

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.user import User


def format_user_summary(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "phone": user.phone,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "presence_status": user.presence_status.value if user.presence_status else None,
        "last_seen": user.last_seen.isoformat() if user.last_seen else None,
        "is_verified": user.is_verified,
    }


def format_contact(contact: Contact) -> dict[str, Any]:
    contact_user = contact.contact_user
    return {
        "id": str(contact.id),
        "owner_id": str(contact.owner_id),
        "contact_user_id": str(contact.contact_user_id),
        "nickname": contact.nickname,
        "contact_user": format_user_summary(contact_user) if contact_user else None,
    }


def format_message(message: Message) -> dict[str, Any]:
    from sqlalchemy.orm.attributes import instance_state
    
    state = instance_state(message)
    attachments_loaded = "attachments" in state.dict
    reactions_loaded = "reactions" in state.dict
    receipts_loaded = "receipts" in state.dict

    return {
        "id": str(message.id),
        "conversation_id": str(message.conversation_id),
        "sender_id": str(message.sender_id),
        "content": message.content,
        "message_type": message.message_type.value if message.message_type else None,
        "reply_to_id": str(message.reply_to_id) if message.reply_to_id else None,
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "expires_at": message.expires_at.isoformat() if message.expires_at else None,
        "forwarded_from_id": str(message.forwarded_from_id) if message.forwarded_from_id else None,
        "is_system": message.is_system,
        "client_message_id": message.client_message_id,
        "scheduled_at": message.scheduled_at.isoformat() if message.scheduled_at else None,
        "is_draft": message.is_draft,
        "is_pinned": message.is_pinned,
        "created_at": message.created_at.isoformat(),
        "updated_at": message.updated_at.isoformat(),
        "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
        "attachments": [
            {
                "id": str(attachment.id),
                "storage_key": attachment.storage_key,
                "original_filename": attachment.original_filename,
                "mime_type": attachment.mime_type,
                "size": attachment.size,
                "width": attachment.width,
                "height": attachment.height,
                "duration": attachment.duration,
                "thumbnail_url": attachment.thumbnail_url,
                "checksum": attachment.checksum,
            }
            for attachment in message.attachments
        ] if attachments_loaded and message.attachments else [],
        "reactions": [
            {
                "id": str(reaction.id),
                "user_id": str(reaction.user_id),
                "reaction": reaction.reaction,
                "unicode": reaction.unicode,
            }
            for reaction in message.reactions
        ] if reactions_loaded and message.reactions else [],
        "receipts": [
            {
                "id": str(receipt.id),
                "user_id": str(receipt.user_id),
                "status": receipt.status.value if receipt.status else None,
                "updated_at": receipt.updated_at.isoformat(),
            }
            for receipt in message.receipts
        ] if receipts_loaded and message.receipts else [],
    }


def format_conversation_member(member: ConversationMember) -> dict[str, Any]:
    return {
        "id": str(member.id),
        "conversation_id": str(member.conversation_id),
        "user_id": str(member.user_id),
        "role": member.role.value if member.role else None,
        "nickname": member.nickname,
        "joined_at": member.joined_at.isoformat(),
        "left_at": member.left_at.isoformat() if member.left_at else None,
        "notifications_enabled": member.notifications_enabled,
        "last_read_message_id": str(member.last_read_message_id) if member.last_read_message_id else None,
        "user": format_user_summary(member.user) if getattr(member, "user", None) else None,
    }


def format_conversation(conversation: Conversation) -> dict[str, Any]:
    return {
        "id": str(conversation.id),
        "type": conversation.type.value if conversation.type else None,
        "name": conversation.name,
        "description": conversation.description,
        "avatar_url": conversation.avatar_url,
        "created_by": str(conversation.created_by) if conversation.created_by else None,
        "updated_by": str(conversation.updated_by) if conversation.updated_by else None,
        "last_message_id": str(conversation.last_message_id) if conversation.last_message_id else None,
        "last_activity_at": conversation.last_activity_at.isoformat(),
        "is_archived": conversation.is_archived,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "deleted_at": conversation.deleted_at.isoformat() if conversation.deleted_at else None,
        "members": [
            format_conversation_member(member)
            for member in getattr(conversation, "members", [])
            if member.left_at is None
        ],
        "last_message": format_message(conversation.last_message)
        if getattr(conversation, "last_message", None)
        else None,
    }
