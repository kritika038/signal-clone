import pytest
import pytest_asyncio
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, ANY

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.models.enums import PresenceStatus
from app.models.user import User
from app.models.user_session import UserSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.contact import Contact
from app.websocket.connection_manager import connection_manager
from app.websocket.presence_manager import presence_manager
from app.websocket.typing_manager import typing_manager, typing_state_store
from app.websocket.gateway import ws_gateway
from app.websocket.manager import connect as ws_connect, disconnect as ws_disconnect
from app.websocket.rooms import get_user_room, get_conversation_room

DATABASE_URL = "sqlite+aiosqlite:///file:ws_test?mode=memory&cache=shared"

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
async def test_ws_authentication_and_lifecycle(db_engine, test_db: AsyncSession):
    # Create test user and contact user
    user = User(
        id=uuid.uuid4(),
        phone="+15550000001",
        hashed_password="hashed_password",
        username="ws_user1"
    )
    user2 = User(
        id=uuid.uuid4(),
        phone="+15550000999",
        hashed_password="hashed_password",
        username="ws_user_contact"
    )
    test_db.add_all([user, user2])
    await test_db.flush()

    # user2 has added user as contact
    contact = Contact(owner_id=user2.id, contact_user_id=user.id, nickname="Friend")
    test_db.add(contact)
    await test_db.commit()
    
    session_id = uuid.uuid4()
    # Create valid JWT
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    token = jwt.encode(
        {"sub": str(user.id), "session_id": str(session_id), "exp": exp},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    # 1. Connect without auth details - should fail
    res = await ws_connect("socket_1", {}, auth=None)
    assert res is False
    
    # 2. Connect with invalid token - should fail
    res = await ws_connect("socket_1", {}, auth={"token": "invalid"})
    assert res is False
    
    # 3. Connect with active session in database - should pass
    sess = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    test_db.add(sess)
    await test_db.commit()
    
    with patch("app.websocket.manager.sio.enter_room", new_callable=AsyncMock) as mock_enter:
        res = await ws_connect("socket_1", {}, auth={"token": token})
        assert res is True
        assert connection_manager.get_user_id("socket_1") == str(user.id)
        assert connection_manager.is_user_online(user.id) is True
        
        # Verify rooms joined automatically
        mock_enter.assert_any_call("socket_1", get_user_room(user.id))
        
    # Mark user2 as online in connection manager so they receive presence broadcast
    connection_manager.connect("socket_contact", str(user2.id))

    # 4. Disconnect socket
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        await ws_disconnect("socket_1")
        assert connection_manager.get_user_id("socket_1") is None
        assert connection_manager.is_user_online(user.id) is False
        
        # Verify presence OFFLINE broadcast was triggered to user2's private room
        mock_emit.assert_called_with("presence.update", {
            "user_id": str(user.id),
            "status": "OFFLINE",
            "last_seen": ANY
        }, to=get_user_room(user2.id))

@pytest.mark.asyncio
async def test_ws_rooms_sync(db_engine, test_db: AsyncSession):
    # Setup users and active memberships
    user = User(id=uuid.uuid4(), phone="+15550000002", hashed_password="pw", username="ws_user2")
    conv1 = Conversation(type="GROUP")
    conv2 = Conversation(type="GROUP")
    test_db.add_all([user, conv1, conv2])
    await test_db.flush()
    
    m1 = ConversationMember(conversation_id=conv1.id, user_id=user.id, role="MEMBER")
    m2 = ConversationMember(conversation_id=conv2.id, user_id=user.id, role="MEMBER")
    test_db.add_all([m1, m2])
    await test_db.commit()
    
    session_id = uuid.uuid4()
    sess = UserSession(id=session_id, user_id=user.id, refresh_token_hash="hash", expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    test_db.add(sess)
    await test_db.commit()
    
    token = jwt.encode(
        {"sub": str(user.id), "session_id": str(session_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    with patch("app.websocket.manager.sio.enter_room", new_callable=AsyncMock) as mock_enter:
        res = await ws_connect("socket_2", {}, auth={"token": token})
        assert res is True
        # Verify user joined both conversation rooms
        mock_enter.assert_any_call("socket_2", get_conversation_room(conv1.id))
        mock_enter.assert_any_call("socket_2", get_conversation_room(conv2.id))

@pytest.mark.asyncio
async def test_heartbeat_and_cleanup():
    connection_manager.connect("socket_stale", "user_stale")
    connection_manager.record_activity("socket_stale")
    
    # Verify not stale initially
    stale = connection_manager.get_stale_sockets(timeout_seconds=5)
    assert len(stale) == 0
    
    # Mock time delay
    with patch("app.websocket.connection_manager.datetime") as mock_date:
        # Shift current time forward by 10 seconds
        mock_date.now.return_value = datetime.now(timezone.utc) + timedelta(seconds=10)
        stale = connection_manager.get_stale_sockets(timeout_seconds=5)
        assert "socket_stale" in stale

@pytest.mark.asyncio
async def test_typing_events_broadcast():
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    with patch("app.websocket.manager.sio.emit", new_callable=AsyncMock) as mock_emit:
        await typing_manager.set_typing(conv_id, user_id, is_typing=True)
        # Check in typing state store
        active = await typing_state_store.get_typing_users(str(conv_id))
        assert str(user_id) in active
        
        # Verify typing.start broadcast
        mock_emit.assert_called_with("typing.start", {
            "conversation_id": str(conv_id),
            "user_id": str(user_id)
        }, to=get_conversation_room(conv_id))
        
        await typing_manager.set_typing(conv_id, user_id, is_typing=False)
        active = await typing_state_store.get_typing_users(str(conv_id))
        assert str(user_id) not in active
        
        # Verify typing.stop broadcast
        mock_emit.assert_called_with("typing.stop", {
            "conversation_id": str(conv_id),
            "user_id": str(user_id)
        }, to=get_conversation_room(conv_id))
