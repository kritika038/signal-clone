import pytest
import pytest_asyncio
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, ANY
from jose import jwt

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, and_

from app.core.config import settings
from app.db.base import Base
from app.models.user import User
from app.models.user_session import UserSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.conversation_preference import ConversationPreference
from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.models.message_reaction import MessageReaction
from app.models.starred_message import StarredMessage
from app.models.message_deleted_for_me import MessageDeletedForMe
from app.models.conversation_draft import ConversationDraft
from app.models.attachment import Attachment
from app.models.enums import ReceiptStatus, MessageType
from app.websocket.connection_manager import connection_manager
from app.websocket.gateway import ws_gateway
from app.websocket.manager import connect as ws_connect
from app.websocket.rooms import get_conversation_room, get_user_room
from app.services.message_service import MessageService
from app.services.draft_service import DraftService
from app.services.scheduled_message_service import ScheduledMessageService
from app.services.disappearing_message_service import DisappearingMessageService
from app.services.storage_provider import LocalStorageProvider

DATABASE_URL = "sqlite+aiosqlite:///file:adv_msg_test?mode=memory&cache=shared"

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False, "uri": True})
    keep_alive_conn = await engine.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await keep_alive_conn.close()
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_db(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

@pytest.fixture(scope="function", autouse=True)
def patch_db_session(db_engine):
    import app.db.session
    import app.websocket.auth
    import app.websocket.gateway
    
    app.db.session.SessionLocal.configure(bind=db_engine)
    app.websocket.auth.SessionLocal.configure(bind=db_engine)
    app.websocket.gateway.SessionLocal.configure(bind=db_engine)
    
    connection_manager._socket_to_user.clear()
    connection_manager._user_to_sockets.clear()
    connection_manager._socket_rooms.clear()
    connection_manager._last_activity.clear()

@pytest.mark.asyncio
async def test_duplicate_client_message_id_idempotency(db_engine, test_db: AsyncSession):
    # Setup conversation
    u1 = User(id=uuid.uuid4(), phone="+15559000001", hashed_password="pw", username="sender")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    msg_service = MessageService(test_db)
    client_id = "unique_client_ref_123"

    # Send first time
    msg1 = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Idempotent content",
        client_message_id=client_id
    )

    # Send second time with same client_message_id
    msg2 = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Idempotent content duplicate attempt",
        client_message_id=client_id
    )

    assert msg1.id == msg2.id
    assert msg2.content == "Idempotent content"  # Retained original content

@pytest.mark.asyncio
async def test_message_replies_and_quotes(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000002", hashed_password="pw", username="sender")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    msg_service = MessageService(test_db)
    parent = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Original parent message"
    )

    reply = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="This is a reply quote",
        reply_to_id=parent.id
    )

    assert reply.reply_to_id == parent.id

@pytest.mark.asyncio
async def test_message_forwarding(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000003", hashed_password="pw", username="sender")
    conv1 = Conversation(type="DIRECT")
    conv2 = Conversation(type="DIRECT")
    test_db.add_all([u1, conv1, conv2])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv1.id, user_id=u1.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv2.id, user_id=u1.id, role="MEMBER")
    test_db.add_all([m1, m2])
    await test_db.commit()

    msg_service = MessageService(test_db)
    original = await msg_service.send_new_message(
        conversation_id=conv1.id,
        sender_id=u1.id,
        content="Forward this content"
    )

    forwarded = await msg_service.forward_message(
        target_conversation_id=conv2.id,
        sender_id=u1.id,
        message_id=original.id
    )

    assert forwarded.content == "Forward this content"
    assert forwarded.conversation_id == conv2.id
    assert forwarded.forwarded_from_id == u1.id

@pytest.mark.asyncio
async def test_message_delete_for_everyone(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000004", hashed_password="pw", username="sender")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    msg_service = MessageService(test_db)
    msg = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Delete for everyone content"
    )

    # Delete for everyone (soft delete)
    deleted = await msg_service.delete_for_everyone(msg.id, u1.id)
    assert deleted.deleted_at is not None

@pytest.mark.asyncio
async def test_message_delete_for_me(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000005", hashed_password="pw", username="user1")
    u2 = User(id=uuid.uuid4(), phone="+15559000006", hashed_password="pw", username="user2")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, u2, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role="MEMBER")
    test_db.add_all([m1, m2])
    await test_db.commit()

    msg_service = MessageService(test_db)
    msg = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Content to hide for user 1"
    )

    # Delete for user 1
    await msg_service.delete_for_me(msg.id, u1.id)

    # Verify record in deleted_for_me exists
    res = await test_db.execute(
        select(MessageDeletedForMe).where(
            and_(
                MessageDeletedForMe.message_id == msg.id,
                MessageDeletedForMe.user_id == u1.id
            )
        )
    )
    assert res.scalar_one_or_none() is not None

    # Verify not deleted for user 2
    res2 = await test_db.execute(
        select(MessageDeletedForMe).where(
            and_(
                MessageDeletedForMe.message_id == msg.id,
                MessageDeletedForMe.user_id == u2.id
            )
        )
    )
    assert res2.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_pin_and_star_message(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000007", hashed_password="pw", username="user")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    msg_service = MessageService(test_db)
    msg = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Pin and star me"
    )

    # Test Pinning
    pinned = await msg_service.toggle_pin_message(msg.id, u1.id)
    assert pinned is True
    assert msg.is_pinned is True

    # Test Starring
    starred = await msg_service.toggle_star_message(msg.id, u1.id)
    assert starred is True
    
    starred_list = await msg_service.get_starred_messages(u1.id)
    assert len(starred_list) == 1
    assert starred_list[0].id == msg.id

@pytest.mark.asyncio
async def test_emoji_reactions(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000008", hashed_password="pw", username="user")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    msg_service = MessageService(test_db)
    msg = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="React to me"
    )

    connection_manager.connect("socket_user", str(u1.id))

    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        # Toggle reaction (add)
        await ws_gateway.handle_reaction_toggle("socket_user", {
            "message_id": str(msg.id),
            "emoji": "👍"
        })
        mock_emit.assert_called_with("reaction.updated", {
            "message_id": str(msg.id),
            "emoji": "👍",
            "is_active": True,
            "user_id": str(u1.id),
            "count": 1,
            "users": [str(u1.id)]
        }, to=get_conversation_room(conv.id))

        # Toggle reaction (remove)
        await ws_gateway.handle_reaction_toggle("socket_user", {
            "message_id": str(msg.id),
            "emoji": "👍"
        })
        mock_emit.assert_called_with("reaction.updated", {
            "message_id": str(msg.id),
            "emoji": "👍",
            "is_active": False,
            "user_id": str(u1.id),
            "count": 0,
            "users": []
        }, to=get_conversation_room(conv.id))

@pytest.mark.asyncio
async def test_scheduled_message_delivery(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000009", hashed_password="pw", username="sender")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    msg_service = MessageService(test_db)
    future_time = datetime.now(timezone.utc) + timedelta(seconds=1)

    # Save scheduled message
    msg = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Hello from the past!",
        scheduled_at=future_time
    )

    assert msg.scheduled_at.replace(tzinfo=timezone.utc) == future_time

    # Run scheduler daemon processing
    sched_service = ScheduledMessageService()
    
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        # Move system clock forward 2s inside scheduler processing
        with patch("app.services.scheduled_message_service.datetime") as mock_date:
            mock_date.now.return_value = future_time + timedelta(seconds=1)
            await sched_service.process_due_messages()
            
            # Verify socket broadcast triggered
            mock_emit.assert_any_call("message.received", ANY, to=get_conversation_room(conv.id))

        # Check DB states
        await test_db.refresh(msg)
        assert msg.scheduled_at is None

@pytest.mark.asyncio
async def test_disappearing_message_purging(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000010", hashed_password="pw", username="sender")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    pref = ConversationPreference(conversation_id=conv.id, user_id=u1.id, disappearing_timer=30)
    test_db.add_all([m1, pref])
    await test_db.commit()

    msg_service = MessageService(test_db)
    
    # Message sent. The expires_at should automatically be set to now + 30s.
    msg = await msg_service.send_new_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Disappearing content"
    )

    assert msg.expires_at is not None

    # Verify purging daemon
    purger = DisappearingMessageService()
    
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        # Shift purger's date check past expiration time
        with patch("app.services.disappearing_message_service.datetime") as mock_date:
            mock_date.now.return_value = datetime.now(timezone.utc) + timedelta(seconds=40)
            await purger.purge_expired_messages()
            
            # Verify deletion broadcast event sent
            mock_emit.assert_called_with("message.deleted", {
                "message_id": str(msg.id),
                "conversation_id": str(conv.id),
                "is_expired": True
            }, to=get_conversation_room(conv.id))

        # Assert message record is completely deleted from SQLite
        res = await test_db.execute(select(Message).where(Message.id == msg.id))
        assert res.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_conversation_drafts(db_engine, test_db: AsyncSession):
    u1 = User(id=uuid.uuid4(), phone="+15559000011", hashed_password="pw", username="user")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, conv])
    await test_db.flush()
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    test_db.add(m1)
    await test_db.commit()

    draft_service = DraftService(test_db)
    # Save draft
    draft = await draft_service.save_draft(conv.id, u1.id, "Draft text content")
    assert draft.content == "Draft text content"

    # Get draft
    fetched = await draft_service.get_draft(conv.id, u1.id)
    assert fetched.content == "Draft text content"

    # Delete draft
    cleared = await draft_service.clear_draft(conv.id, u1.id)
    assert cleared is True
    
    # Assert deleted
    assert await draft_service.get_draft(conv.id, u1.id) is None

@pytest.mark.asyncio
async def test_attachment_handling_and_validation(db_engine, test_db: AsyncSession):
    provider = LocalStorageProvider(upload_dir="./storage_test")
    file_bytes = b"This is dummy text representing a voice note or image content."
    
    # 1. Successful upload within limit
    upload_res = await provider.upload_file(file_bytes, "voicenote.wav", "audio/wav")
    assert upload_res["size"] == len(file_bytes)
    assert upload_res["original_filename"] == "voicenote.wav"
    assert upload_res["checksum"] is not None

    # 2. Upload file exceeding 10MB limit (e.g. 11MB)
    large_bytes = b"a" * (11 * 1024 * 1024)
    with pytest.raises(ValueError, match="File exceeds maximum limit of 10MB"):
        await provider.upload_file(large_bytes, "heavy.mp4", "video/mp4")

    # 3. Upload unsupported mime type
    with pytest.raises(ValueError, match="is not supported"):
        await provider.upload_file(file_bytes, "script.exe", "application/octet-stream")

    # Clean up uploaded files
    await provider.delete_file(upload_res["storage_key"])
