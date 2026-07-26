import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, ANY

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.models.enums import PresenceStatus, ReceiptStatus, MessageType
from app.models.user import User
from app.models.user_session import UserSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.models.blocked_user import BlockedUser
from app.websocket.connection_manager import connection_manager
from app.websocket.gateway import ws_gateway
from app.websocket.manager import connect as ws_connect, disconnect as ws_disconnect
from app.websocket.rooms import get_conversation_room, get_user_room

DATABASE_URL = "sqlite+aiosqlite:///file:msg_test?mode=memory&cache=shared"

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
def patch_db_session(db_engine, monkeypatch):
    import app.db.session
    import app.websocket.auth
    import app.websocket.gateway
    
    app.db.session.SessionLocal.configure(bind=db_engine)
    app.websocket.auth.SessionLocal.configure(bind=db_engine)
    app.websocket.gateway.SessionLocal.configure(bind=db_engine)
    
    # Reset connection manager
    connection_manager._socket_to_user.clear()
    connection_manager._user_to_sockets.clear()
    connection_manager._socket_rooms.clear()
    connection_manager._last_activity.clear()

@pytest.mark.asyncio
async def test_private_messaging_flow(db_engine, test_db: AsyncSession):
    # Setup two users
    u1 = User(id=uuid.uuid4(), phone="+15550000003", hashed_password="pw", username="sender")
    u2 = User(id=uuid.uuid4(), phone="+15550000004", hashed_password="pw", username="recipient")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, u2, conv])
    await test_db.flush()
    
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role="MEMBER")
    test_db.add_all([m1, m2])
    await test_db.commit()
    
    # Bind sender and recipient sockets
    connection_manager.connect("sid_sender", str(u1.id))
    connection_manager.connect("sid_recipient", str(u2.id))
    
    send_payload = {
        "conversation_id": str(conv.id),
        "content": "Hello private chat!"
    }
    
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        await ws_gateway.handle_message_send("sid_sender", send_payload)
        
        # Verify message.sent acknowledged to sender
        mock_emit.assert_any_call("message.sent", ANY, to="sid_sender")
        
        # Verify message.received broadcasted to the conversation room
        mock_emit.assert_any_call("message.received", ANY, to=get_conversation_room(conv.id), skip_sid="sid_sender")
        
        # Verify optimistic delivery (since recipient is online)
        mock_emit.assert_any_call("message.delivered", ANY, to=get_user_room(u1.id))

@pytest.mark.asyncio
async def test_offline_message_sync(db_engine, test_db: AsyncSession):
    # Setup users
    u1 = User(id=uuid.uuid4(), phone="+15550000005", hashed_password="pw", username="sender_offline")
    u2 = User(id=uuid.uuid4(), phone="+15550000006", hashed_password="pw", username="recipient_offline")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, u2, conv])
    await test_db.flush()
    
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role="MEMBER")
    test_db.add_all([m1, m2])
    await test_db.commit()
    
    # Recipient u2 is offline (no sockets registered). Sender u1 is online.
    connection_manager.connect("sid_sender", str(u1.id))
    
    send_payload = {
        "conversation_id": str(conv.id),
        "content": "Sent while you were offline!"
    }
    
    await ws_gateway.handle_message_send("sid_sender", send_payload)
    
    # Verify receipt generated in database as SENT for u2
    from sqlalchemy import select
    res_r = await test_db.execute(select(MessageReceipt).where(MessageReceipt.user_id == u2.id))
    receipt = res_r.scalar_one()
    assert receipt.status == ReceiptStatus.SENT
    
    # Recipient connects
    session_id = uuid.uuid4()
    sess = UserSession(id=session_id, user_id=u2.id, refresh_token_hash="hash", expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    test_db.add(sess)
    await test_db.commit()
    
    token = jwt.encode(
        {"sub": str(u2.id), "session_id": str(session_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    # Patch both emit and enter_room during connection to mock socketio
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit, \
         patch("app.websocket.manager.sio.enter_room", new_callable=AsyncMock) as mock_enter:
        res = await ws_connect("sid_recipient_reconnect", {}, auth={"token": token})
        assert res is True
        
        # Verify offline message is delivered to recipient socket
        mock_emit.assert_any_call("message.received", ANY, to="sid_recipient_reconnect")
        
        # Verify sender notified of delivery
        mock_emit.assert_any_call("message.delivered", {
            "message_id": str(receipt.message_id),
            "user_id": str(u2.id)
        }, to=get_user_room(u1.id))
        
        # Refresh and verify db receipt updated to DELIVERED
        await test_db.refresh(receipt)
        assert receipt.status == ReceiptStatus.DELIVERED

@pytest.mark.asyncio
async def test_message_read_receipt(db_engine, test_db: AsyncSession):
    # Setup message in db
    u1 = User(id=uuid.uuid4(), phone="+15550000007", hashed_password="pw", username="sender_receipt")
    u2 = User(id=uuid.uuid4(), phone="+15550000008", hashed_password="pw", username="recipient_receipt")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, u2, conv])
    await test_db.flush()
    
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role="MEMBER")
    msg = Message(conversation_id=conv.id, sender_id=u1.id, content="Hi")
    test_db.add_all([m1, m2, msg])
    await test_db.flush()
    
    receipt = MessageReceipt(message_id=msg.id, user_id=u2.id, status=ReceiptStatus.DELIVERED)
    test_db.add(receipt)
    await test_db.commit()
    
    connection_manager.connect("sid_recipient", str(u2.id))
    
    # Recipient marks message as READ
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        await ws_gateway.handle_receipt_read("sid_recipient", {"message_id": str(msg.id)})
        
        # Verify sender notified of read state
        mock_emit.assert_called_with("message.read", {
            "message_id": str(msg.id),
            "user_id": str(u2.id)
        }, to=get_user_room(u1.id))
        
        # Verify receipt in DB is updated to READ
        await test_db.refresh(receipt)
        assert receipt.status == ReceiptStatus.READ
        
        # Verify member's last_read_message_id is updated
        await test_db.refresh(m2)
        assert m2.last_read_message_id == msg.id

@pytest.mark.asyncio
async def test_messaging_blocked_constraint(db_engine, test_db: AsyncSession):
    # Setup users and direct chat
    u1 = User(id=uuid.uuid4(), phone="+15550000009", hashed_password="pw", username="sender_blocked")
    u2 = User(id=uuid.uuid4(), phone="+15550000010", hashed_password="pw", username="recipient_blocked")
    conv = Conversation(type="DIRECT")
    test_db.add_all([u1, u2, conv])
    await test_db.flush()
    
    m1 = ConversationMember(conversation_id=conv.id, user_id=u1.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv.id, user_id=u2.id, role="MEMBER")
    # u2 blocks u1
    block = BlockedUser(user_id=u2.id, blocked_user_id=u1.id)
    test_db.add_all([m1, m2, block])
    await test_db.commit()
    
    connection_manager.connect("sid_sender", str(u1.id))
    
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        # u1 attempts to send message to conv (should fail due to block)
        await ws_gateway.handle_message_send("sid_sender", {
            "conversation_id": str(conv.id),
            "content": "I am blocked!"
        })
        # Verify error event emitted
        mock_emit.assert_called_with("ws.error", {
            "message": "Cannot send message: Block relationship exists"
        }, to="sid_sender")
