import asyncio
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
import uuid
from fastapi import status
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.db.base import Base
from app.api.deps import get_async_db, global_rate_limiter
from app.core.config import settings
from app.models.enums import PresenceStatus
from app.models.user import User
from app.models.user_session import UserSession
from app.models.user_settings import UserSettings
from app.websocket.auth import authenticate_socket
from app.websocket.manager import ws_manager

# Use shared memory SQLite to allow multiple connections (SessionLocal vs test session) to share the same DB
DATABASE_URL = "sqlite+aiosqlite:///file:auth_test?mode=memory&cache=shared"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """
    Fresh in-memory shared SQLite engine.
    """
    # check_same_thread: False and cache=shared allows multi-session concurrency in tests
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False, "uri": True}, echo=True)
    
    # We must keep a connection open to keep the shared memory DB alive
    keep_alive_conn = await engine.connect()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    await keep_alive_conn.close()
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """
    Spawns session linked to test database.
    """
    session_factory = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

@pytest.fixture(scope="function", autouse=True)
def patch_websocket_session(db_engine, monkeypatch):
    """
    Monkeypatches the SessionLocal of both app.db.session and app.websocket.auth.
    """
    import app.db.session
    import app.websocket.auth
    app.db.session.SessionLocal.configure(bind=db_engine)
    app.websocket.auth.SessionLocal.configure(bind=db_engine)

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    """
    Async client for endpoint routing test validations.
    """
    async def override_db():
        yield db_session

    fastapi_app = app.other_asgi_app
    fastapi_app.dependency_overrides[get_async_db] = override_db
    
    global_rate_limiter._requests.clear()
    global_otp_store._store.clear()
    
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client
        
    fastapi_app.dependency_overrides.clear()

# --- Auth Test Cases ---

@pytest.mark.asyncio
async def test_full_auth_registration_lifecycle(async_client):
    # 1. Send OTP
    send_payload = {
        "phone": "+15555550001",
        "email": "alice@example.com"
    }
    response = await async_client.post("/api/v1/auth/otp/send", json=send_payload)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Get OTP from otp_store directly for testing
    payload = global_otp_store._store.get("+15555550001")
    assert payload is not None
    otp = payload["otp"]

    # 2. OTP verification (Invalid OTP)
    verify_payload_invalid = {
        "phone": "+15555550001",
        "email": "alice@example.com",
        "otp": "000000"
    }
    verify_res_invalid = await async_client.post("/api/v1/auth/otp/verify", json=verify_payload_invalid)
    assert verify_res_invalid.status_code == 400
    assert verify_res_invalid.json()["success"] is False

    # 3. OTP verification (Valid OTP)
    verify_payload_valid = {
        "phone": "+15555550001",
        "email": "alice@example.com",
        "otp": otp
    }
    verify_res_valid = await async_client.post("/api/v1/auth/otp/verify", json=verify_payload_valid)
    assert verify_res_valid.status_code == 200
    data = verify_res_valid.json()["data"]
    registration_token = data["registration_token"]
    assert registration_token is not None

    # 4. Registration
    reg_payload = {
        "registration_token": registration_token,
        "phone": "+15555550001",
        "email": "alice@example.com",
        "username": "alice",
        
        "display_name": "Alice Smith"
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    print(reg_res.json()); assert reg_res.status_code == 200
    data = reg_res.json()["data"]
    assert data["user"]["phone"] == "+15555550001"
    assert data["tokens"]["access_token"] is not None

    # 5. Duplicate Check
    dup_res = await async_client.post("/api/v1/auth/otp/send", json=send_payload)
    assert dup_res.status_code == 400
    assert dup_res.json()["success"] is False
    assert "already registered" in dup_res.json()["error"]["message"]

@pytest.mark.asyncio
async def test_login_and_logout_lifecycle(async_client):
    # Setup user
    await async_client.post("/api/v1/auth/otp/send", json={"phone": "+15555550002", "email": "bob@example.com"})
    otp = global_otp_store._store.get("+15555550002")["otp"]
    res = await async_client.post("/api/v1/auth/otp/verify", json={"phone": "+15555550002", "email": "bob@example.com", "otp": otp})
    registration_token = res.json()["data"]["registration_token"]
    await async_client.post("/api/v1/auth/register", json={
        "registration_token": registration_token, "phone": "+15555550002", "email": "bob@example.com", "username": "bob", "display_name": "Bob J"
    })

    # 1. Login with Phone
    login_phone = await async_client.post("/api/v1/auth/login", json={
        "login_id": "+15555550002", 
    })
    assert login_phone.status_code == 200
    access_token = login_phone.json()["data"]["tokens"]["access_token"]

    # 2. Login with Username
    login_username = await async_client.post("/api/v1/auth/login", json={
        "login_id": "bob", 
    })
    assert login_username.status_code == 200

    # 3. Login Incorrect Password
    login_fail = await async_client.post("/api/v1/auth/login", json={
        "login_id": "bob", 
    })
    assert login_fail.status_code == 401
    assert login_fail.json()["success"] is False

    # 4. Access Protected Route
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["username"] == "bob"

    # 5. Logout
    logout_res = await async_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # 6. Try Access Protected Route again (fails since session revoked)
    me_res_revoked = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res_revoked.status_code == 401
    assert "Session has expired" in me_res_revoked.json()["error"]["message"]

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_attack(async_client):
    await async_client.post("/api/v1/auth/otp/send", json={"phone": "+15555550003", "email": "charlie@example.com"})
    otp = global_otp_store._store.get("+15555550003")["otp"]
    res = await async_client.post("/api/v1/auth/otp/verify", json={"phone": "+15555550003", "email": "charlie@example.com", "otp": otp})
    registration_token = res.json()["data"]["registration_token"]
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "registration_token": registration_token, "phone": "+15555550003", "email": "charlie@example.com", "username": "charlie", "display_name": "Charlie"
    })
    tokens = reg_res.json()["data"]["tokens"]
    
    # 1. Valid Refresh
    refresh_res = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()["data"]
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # 2. Reuse Attack: Attempt using the old refresh token again
    reuse_res = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse_res.status_code == 401
    assert "Token reuse detected" in reuse_res.json()["error"]["message"]

    # 3. Verify session is completely revoked - new refresh token is also rejected now
    second_refresh = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert second_refresh.status_code == 401

@pytest.mark.asyncio
async def test_profile_modification_and_session_details(async_client):
    await async_client.post("/api/v1/auth/otp/send", json={"phone": "+15555550004", "email": "dana@example.com"})
    otp = global_otp_store._store.get("+15555550004")["otp"]
    res = await async_client.post("/api/v1/auth/otp/verify", json={"phone": "+15555550004", "email": "dana@example.com", "otp": otp})
    registration_token = res.json()["data"]["registration_token"]
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "registration_token": registration_token, "phone": "+15555550004", "email": "dana@example.com", "username": "dana", "display_name": "Dana S"
    })
    access_token = reg_res.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Get Session details
    session_res = await async_client.get("/api/v1/auth/session", headers=headers)
    assert session_res.status_code == 200
    assert session_res.json()["data"]["device_name"] is not None

    # 2. Update Profile Settings
    patch_payload = {
        "display_name": "Agent Scully",
        "bio": "I want to believe",
        "theme": "light",
        "privacy_read_receipts": False
    }
    patch_res = await async_client.patch("/api/v1/auth/me", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    patched_data = patch_res.json()["data"]
    assert patched_data["display_name"] == "Agent Scully"
    assert patched_data["bio"] == "I want to believe"
    assert patched_data["settings"]["theme"] == "light"
    assert patched_data["settings"]["privacy_read_receipts"] is False

@pytest.mark.asyncio
async def test_rate_limiting_register(async_client):
    payload = {
        "phone": "+15555550005", "email": "limiter@example.com"
    }
    for _ in range(5):
        res = await async_client.post("/api/v1/auth/otp/send", json=payload)
        assert res.status_code in [200, 400]

    # 6th request triggers rate limit
    res_limited = await async_client.post("/api/v1/auth/otp/send", json=payload)
    assert res_limited.status_code == 429
    assert res_limited.json()["success"] is False
    assert "limit exceeded" in res_limited.json()["error"]["message"]

@pytest.mark.asyncio
async def test_websocket_handshake_authentication(db_session: AsyncSession):
    # Setup database record
    user = User(
        id=uuid.uuid4(),
        phone="+15555550006",
        username="ws_user",
        display_name="WS User",
        hashed_password="pw"
    )
    db_session.add(user)
    await db_session.commit()

    session_id = uuid.uuid4()
    # Create valid JWT token
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    access_token_payload = {
        "sub": str(user.id),
        "session_id": str(session_id),
        "exp": exp
    }
    token = jwt.encode(access_token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # 1. Reject invalid session (revoked session not in db)
    auth_payload_revoked = {"token": token}
    res_revoked = await authenticate_socket(auth_payload_revoked)
    assert res_revoked is None

    # 2. Add Session in DB
    user_sess = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(user_sess)
    await db_session.commit()

    # 3. Successful Handshake


    res_success = await authenticate_socket({"token": token})
    assert res_success is not None
    auth_user, auth_sess = res_success
    assert auth_user.phone == "+15555550006"
    assert auth_sess.id == session_id

    # 4. Reject Deleted User
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()
    
    res_deleted = await authenticate_socket({"token": token})
    assert res_deleted is None
