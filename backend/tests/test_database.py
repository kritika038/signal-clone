import asyncio
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.enums import ConversationType, MessageType, PresenceStatus, ConversationRole, ReceiptStatus
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.user_session import UserSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.repositories.user import UserRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.group import GroupRepository
from app.repositories.message import MessageRepository

# Config in-memory SQLite for testing async engine
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Creates a fresh in-memory SQLite database, runs metadata create,
    yields an AsyncSession, and tears down after test completes.
    """
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    
    async with engine.begin() as conn:
        # Create all tables dynamically
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with session_factory() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_repository_create_and_fetch(db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    
    # Create User
    new_user = User(
        id=uuid.uuid4(),
        phone="+15005550001",
        username="tester1",
        display_name="Tester One",
        hashed_password="hashed_tester_password",
        presence_status=PresenceStatus.ONLINE
    )
    db_session.add(new_user)
    await db_session.commit()
    
    # Fetch by phone
    fetched = await user_repo.get_by_phone_number("+15005550001")
    assert fetched is not None
    assert fetched.username == "tester1"
    assert fetched.display_name == "Tester One"

@pytest.mark.asyncio
async def test_cascade_delete_user(db_session: AsyncSession):
    """
    Ensures that deleting a user deletes their UserSettings and UserSessions in a cascade fashion.
    """
    user_id = uuid.uuid4()
    
    user = User(
        id=user_id,
        phone="+15005550002",
        username="cascade_test",
        display_name="Cascade Test",
        hashed_password="some_password"
    )
    db_session.add(user)
    await db_session.flush()
    
    settings = UserSettings(user_id=user_id, theme="dark")
    session = UserSession(
        user_id=user_id,
        refresh_token_hash="token_hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add_all([settings, session])
    await db_session.commit()
    
    # Verify records exist
    res_set = await db_session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    assert res_set.scalar_one_or_none() is not None
    
    res_sess = await db_session.execute(select(UserSession).where(UserSession.user_id == user_id))
    assert res_sess.scalar_one_or_none() is not None
    
    # Delete User
    await db_session.delete(user)
    await db_session.commit()
    
    # Verify cascaded deletion
    res_set = await db_session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    assert res_set.scalar_one_or_none() is None
    
    res_sess = await db_session.execute(select(UserSession).where(UserSession.user_id == user_id))
    assert res_sess.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_direct_conversation_creation(db_session: AsyncSession):
    conv_repo = ConversationRepository(db_session)
    
    u1 = User(id=uuid.uuid4(), phone="+15005559001", hashed_password="pw")
    u2 = User(id=uuid.uuid4(), phone="+15005559002", hashed_password="pw")
    db_session.add_all([u1, u2])
    await db_session.commit()
    
    # Create direct chat
    conv = await conv_repo.create_direct_chat(u1.id, u2.id)
    assert conv.type == ConversationType.DIRECT
    
    # Fetch members count
    res_m = await db_session.execute(select(ConversationMember).where(ConversationMember.conversation_id == conv.id))
    members = res_m.scalars().all()
    assert len(members) == 2
    assert {m.user_id for m in members} == {u1.id, u2.id}

@pytest.mark.asyncio
async def test_group_conversation_creation_and_member_add(db_session: AsyncSession):
    group_repo = GroupRepository(db_session)
    
    creator = User(id=uuid.uuid4(), phone="+15005559101", hashed_password="pw")
    m1 = User(id=uuid.uuid4(), phone="+15005559102", hashed_password="pw")
    m2 = User(id=uuid.uuid4(), phone="+15005559103", hashed_password="pw")
    db_session.add_all([creator, m1, m2])
    await db_session.commit()
    
    # Create group
    group = await group_repo.create_group(
        name="Team Signal",
        description="Testing Signal Backend",
        creator_id=creator.id,
        member_ids=[m1.id, m2.id]
    )
    
    assert group.type == ConversationType.GROUP
    assert group.name == "Team Signal"
    
    # Verify creator is Owner
    owner_query = select(ConversationMember).where(
        ConversationMember.conversation_id == group.id,
        ConversationMember.user_id == creator.id
    )
    owner_res = await db_session.execute(owner_query)
    owner = owner_res.scalar_one()
    assert owner.role == ConversationRole.OWNER

    # Remove member
    removed = await group_repo.remove_member(group.id, m1.id)
    assert removed is True
    
    # Verify member has left_at set
    left_query = select(ConversationMember).where(
        ConversationMember.conversation_id == group.id,
        ConversationMember.user_id == m1.id
    )
    left_res = await db_session.execute(left_query)
    left_member = left_res.scalar_one()
    assert left_member.left_at is not None

@pytest.mark.asyncio
async def test_message_sending_receipts_replies_reactions(db_session: AsyncSession):
    msg_repo = MessageRepository(db_session)
    
    u1 = User(id=uuid.uuid4(), phone="+15005558001", hashed_password="pw")
    u2 = User(id=uuid.uuid4(), phone="+15005558002", hashed_password="pw")
    db_session.add_all([u1, u2])
    await db_session.commit()
    
    conv_repo = ConversationRepository(db_session)
    conv = await conv_repo.create_direct_chat(u1.id, u2.id)
    
    # Send message from u1 to u2
    msg = await msg_repo.send_message(
        conversation_id=conv.id,
        sender_id=u1.id,
        content="Hello world!"
    )
    
    assert msg.content == "Hello world!"
    assert msg.conversation_id == conv.id
    assert msg.sender_id == u1.id
    
    # Verify Receipts generated
    receipts_query = select(MessageReceipt).where(MessageReceipt.message_id == msg.id)
    receipts_res = await db_session.execute(receipts_query)
    receipts = receipts_res.scalars().all()
    assert len(receipts) == 2  # Sender and recipient
    
    # Sender receipt is READ, recipient is SENT
    sender_receipt = next(r for r in receipts if r.user_id == u1.id)
    recipient_receipt = next(r for r in receipts if r.user_id == u2.id)
    assert sender_receipt.status == ReceiptStatus.READ
    assert recipient_receipt.status == ReceiptStatus.SENT
    
    # Mark read by recipient
    await msg_repo.mark_read(msg.id, u2.id)
    await db_session.refresh(recipient_receipt)
    assert recipient_receipt.status == ReceiptStatus.READ

    # Add reaction
    reaction = await msg_repo.add_reaction(msg.id, u2.id, "👍", "U+1F44D")
    assert reaction.reaction == "👍"
    assert reaction.unicode == "U+1F44D"

@pytest.mark.asyncio
async def test_seed_integrity(db_session: AsyncSession):
    from app.db.seed import seed_data
    from app.models.conversation import Conversation
    from app.models.message import Message
    
    # Run seed script on the test database session
    await seed_data(db_session)
    
    # Verify Users count
    res_u = await db_session.execute(select(User))
    users = res_u.scalars().all()
    assert len(users) == 12
    
    # Verify Conversations count
    res_c = await db_session.execute(select(Conversation))
    convs = res_c.scalars().all()
    direct_convs = [c for c in convs if c.type == ConversationType.DIRECT]
    group_convs = [c for c in convs if c.type == ConversationType.GROUP]
    
    assert len(direct_convs) == 20
    assert len(group_convs) == 8
    
    # Verify Messages count
    res_m = await db_session.execute(select(Message))
    messages = res_m.scalars().all()
    assert len(messages) >= 2500

