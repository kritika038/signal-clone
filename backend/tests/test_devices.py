import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone, timedelta
from jose import jwt
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.db.base import Base
from app.api.deps import get_async_db
from app.core.config import settings
from app.models.user import User
from app.models.user_session import UserSession
from app.services.device_token_service import DeviceTokenService

DATABASE_URL = "sqlite+aiosqlite:///file:device_test?mode=memory&cache=shared"


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


@pytest_asyncio.fixture(scope="function")
async def async_client(test_db):
    async def _get_test_db():
        yield test_db

    fastapi_app = app.other_asgi_app
    fastapi_app.dependency_overrides[get_async_db] = _get_test_db
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client
    fastapi_app.dependency_overrides.clear()


async def create_user_and_token(db: AsyncSession, phone: str = "+1111111111"):
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    user = User(
        id=user_id,
        phone=phone,
        username=f"user_{user_id.hex[:6]}",
        hashed_password="hashed_pwd",
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    sess = UserSession(
        id=session_id,
        user_id=user_id,
        device_name="Test Phone",
        refresh_token_hash="hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(sess)
    await db.commit()

    payload = {
        "sub": str(user_id),
        "session_id": str(session_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return user, access_token


@pytest.mark.asyncio
async def test_device_registration_and_crud(async_client, test_db):
    user, token = await create_user_and_token(test_db)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register device
    reg_payload = {
        "device_id": "iphone-15-pro",
        "platform": "ios",
        "fcm_token": "fcm_token_sample_12345"
    }
    res = await async_client.post("/api/v1/devices/register", json=reg_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["device_id"] == "iphone-15-pro"
    assert data["data"]["platform"] == "ios"
    assert data["data"]["fcm_token"] == "fcm_token_sample_12345"

    # 2. Get devices
    res_get = await async_client.get("/api/v1/devices", headers=headers)
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["success"] is True
    assert len(get_data["data"]) == 1
    assert get_data["data"][0]["device_id"] == "iphone-15-pro"

    # 3. Update device token
    update_payload = {
        "device_id": "iphone-15-pro",
        "platform": "ios",
        "fcm_token": "refreshed_fcm_token_99999"
    }
    res_up = await async_client.post("/api/v1/devices/register", json=update_payload, headers=headers)
    assert res_up.status_code == 200
    assert res_up.json()["data"]["fcm_token"] == "refreshed_fcm_token_99999"

    # 4. Delete device
    res_del = await async_client.delete("/api/v1/devices/iphone-15-pro", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["data"]["removed"] is True

    # 5. Get devices should now be empty
    res_empty = await async_client.get("/api/v1/devices", headers=headers)
    assert res_empty.status_code == 200
    assert len(res_empty.json()["data"]) == 0


@pytest.mark.asyncio
async def test_registering_token_to_new_account_transfers_ownership(test_db):
    first, _ = await create_user_and_token(test_db, "+1222222222")
    second, _ = await create_user_and_token(test_db, "+1333333333")
    devices = DeviceTokenService(test_db)

    await devices.register_device(first.id, "first-phone", "android", "shared-token")
    transferred = await devices.register_device(second.id, "second-phone", "android", "shared-token")

    assert transferred.user_id == second.id
    assert transferred.device_id == "second-phone"
    assert await devices.get_user_devices(first.id) == []
    assert len(await devices.get_user_devices(second.id)) == 1
