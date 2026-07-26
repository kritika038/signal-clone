import asyncio
from datetime import datetime, timezone, timedelta
import pytest
import pytest_asyncio
import uuid
from fastapi import status
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.base import Base
from app.api.deps import get_async_db, global_rate_limiter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///file:auth_test?mode=memory&cache=shared"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False, "uri": True}, echo=False)
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
    session_factory = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    async def override_db():
        yield db_session
    app.other_asgi_app.dependency_overrides[get_async_db] = override_db
    global_rate_limiter._requests.clear()
    async with AsyncClient(transport=ASGITransport(app=app.other_asgi_app), base_url="http://test") as client:
        yield client
    app.other_asgi_app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_full_auth_lifecycle(async_client):
    # 1. Register OTP Send
    res = await async_client.post("/api/v1/auth/register/send-otp", json={"phone": "+12223334444"})
    assert res.status_code == 200
    assert res.json() == {"success": True, "message": "Verification code sent."}

    # 2. Register OTP Verify (Invalid)
    res = await async_client.post("/api/v1/auth/register/verify", json={"phone": "+12223334444", "otp": "999999"})
    assert res.status_code == 400
    assert res.json()["error"]["message"] == "Invalid verification code."

    # 3. Register OTP Verify (Valid)
    res = await async_client.post("/api/v1/auth/register/verify", json={"phone": "+12223334444", "otp": "123456"})
    assert res.status_code == 200
    reg_token = res.json()["data"]["registration_token"]

    # 4. Register
    res = await async_client.post("/api/v1/auth/register", json={
        "registration_token": reg_token, "username": "tester", "display_name": "Test", "phone": "+12223334444"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()["data"]["tokens"]

    # 5. Login OTP Send
    res = await async_client.post("/api/v1/auth/login/send-otp", json={"login_id": "+12223334444"})
    assert res.status_code == 200

    # 6. Login OTP Verify
    res = await async_client.post("/api/v1/auth/login/verify", json={"login_id": "+12223334444", "otp": "123456"})
    assert res.status_code == 200
    access_token = res.json()["data"]["tokens"]["access_token"]
    
    # 7. Me
    res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200
