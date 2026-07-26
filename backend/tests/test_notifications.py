import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.enums import ConversationType, MessageType
from app.models.user import User
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.services.device_token_service import DeviceTokenService
from app.services.notification_provider import (
    FirebaseNotificationProvider,
    NotificationEvent,
    NotificationPayload,
    NotificationProvider,
    MockNotificationProvider,
)
from app.services.notification_service import NotificationService

DATABASE_URL = "sqlite+aiosqlite:///file:notification_test?mode=memory&cache=shared"


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


class TestProvider(NotificationProvider):
    def __init__(self):
        self.sent_payloads = []
        self.invalid_to_return = []

    async def send(self, payload: NotificationPayload, tokens=None) -> list[str]:
        self.sent_payloads.append((payload, tokens or []))
        return self.invalid_to_return


def test_firebase_multicast_is_chunked_to_fcm_limit():
    tokens = [f"token-{index}" for index in range(1_001)]
    batches = list(FirebaseNotificationProvider._batches(tokens))
    assert [len(batch) for batch in batches] == [500, 500, 1]
    assert batches[0][0] == "token-0"
    assert batches[-1][-1] == "token-1000"


@pytest.mark.asyncio
async def test_notification_sender_suppression_and_events(test_db):
    provider = TestProvider()
    device_service = DeviceTokenService(test_db)
    notification_service = NotificationService(test_db, provider=provider)

    # 1. Create 2 users
    u1_id, u2_id = uuid.uuid4(), uuid.uuid4()
    u1 = User(id=u1_id, phone="+1000000001", username="alice", display_name="Alice", hashed_password="pwd", is_verified=True)
    u2 = User(id=u2_id, phone="+1000000002", username="bob", display_name="Bob", hashed_password="pwd", is_verified=True)
    test_db.add_all([u1, u2])
    await test_db.flush()

    # 2. Register devices for both users
    await device_service.register_device(u1_id, "device_alice", "ios", "fcm_alice_token")
    await device_service.register_device(u2_id, "device_bob", "android", "fcm_bob_token")

    # 3. Create DM conversation
    conv_id = uuid.uuid4()
    conv = Conversation(id=conv_id, type=ConversationType.DIRECT)
    test_db.add(conv)
    await test_db.commit()

    msg = Message(id=uuid.uuid4(), conversation_id=conv_id, sender_id=u1_id, content="Hello Bob", message_type=MessageType.TEXT)

    # 4. Notify new message (Sender: u1, Recipient: [u1, u2])
    await notification_service.notify_new_message(
        message=msg,
        conversation=conv,
        sender=u1,
        recipient_ids=[u1_id, u2_id]
    )

    # 5. Verify only Bob received the notification, Alice (sender) was excluded
    assert len(provider.sent_payloads) == 1
    payload, tokens = provider.sent_payloads[0]
    assert payload.recipient_id == str(u2_id)
    assert payload.event == NotificationEvent.NEW_MESSAGE
    assert tokens == ["fcm_bob_token"]


@pytest.mark.asyncio
async def test_invalid_token_automatic_cleanup(test_db):
    provider = TestProvider()
    provider.invalid_to_return = ["expired_token_123"]

    device_service = DeviceTokenService(test_db)
    notification_service = NotificationService(test_db, provider=provider)

    u_id = uuid.uuid4()
    user = User(id=u_id, phone="+1999999999", username="charlie", hashed_password="pwd", is_verified=True)
    test_db.add(user)
    await test_db.flush()

    await device_service.register_device(u_id, "dev_charlie", "web", "expired_token_123")

    tokens_before = await device_service.get_user_devices(u_id)
    assert len(tokens_before) == 1

    # Send notification which returns invalid token
    payload = NotificationPayload(
        event=NotificationEvent.NEW_MESSAGE,
        recipient_id=str(u_id),
        title="Test",
        body="Test Body",
        data={"type": "direct"}
    )
    await notification_service._send_to_user(u_id, NotificationEvent.NEW_MESSAGE, "Test", "Test Body", {})

    # Invalid token should be cleaned up automatically
    tokens_after = await device_service.get_user_devices(u_id)
    assert len(tokens_after) == 0
