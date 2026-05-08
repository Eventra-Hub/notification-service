import pytest
import fakeredis.aioredis as fakeredis
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
import app.core.redis as redis_module   
from app.main import app
import app.services.notification_store as notification_store

@pytest.fixture(autouse=True)
async def mock_deps():
    fake = fakeredis.FakeRedis(decode_responses=True)
    redis_module.client = fake
    notification_store.client = fake
    mock_connection = MagicMock()
    mock_connection.is_closed = False
    with patch("app.core.rabbitmq.connect_rabbitmq", new_callable=AsyncMock),\
         patch("app.core.rabbitmq.close_rabbitmq",new_callable=AsyncMock),\
         patch("app.core.redis.connect_redis",new_callable=AsyncMock),\
         patch("app.core.redis.close_redis",new_callable=AsyncMock),\
         patch("app.core.rabbitmq.connection", mock_connection):
        yield
    await fake.flushall()

    redis_module.client = None      


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


#  /health 
@pytest.mark.asyncio
async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["redis"] == "connected"


#  POST /notifications/send 
@pytest.mark.asyncio
async def test_send_returns_sent(client):
    r = await client.post("/notifications/send", json={
        "user_id":           "user-001",
        "message":           "Your booking is confirmed.",
        "notification_type": "BOOKING_CONFIRMED",
        "event_id":          "event-999",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert body["notification_id"].startswith("notif:user-001:")

@pytest.mark.asyncio
async def test_send_missing_message_returns_422(client):
    r = await client.post("/notifications/send", json={
        "user_id": "user-001", "notification_type": "BOOKING_CONFIRMED"
    })
    assert r.status_code == 422

@pytest.mark.asyncio
async def test_send_invalid_type_returns_422(client):
    r = await client.post("/notifications/send", json={
        "user_id": "user-001", "message": "hello",
        "notification_type": "NOT_A_REAL_TYPE",
    })
    assert r.status_code == 422


#  GET /notifications/user/{user_id} 
@pytest.mark.asyncio
async def test_get_empty_for_new_user(client):
    r = await client.get("/notifications/user/nobody")
    assert r.status_code == 200
    assert r.json() == []

@pytest.mark.asyncio
async def test_get_returns_newest_first(client):
    for msg in ["First", "Second", "Third"]:
        await client.post("/notifications/send", json={
            "user_id": "user-A", "message": msg,
            "notification_type": "BOOKING_CONFIRMED",
        })
    r = await client.get("/notifications/user/user-A")
    items = r.json()
    assert len(items) == 3
    assert items[0]["message"] == "Third"

@pytest.mark.asyncio
async def test_get_isolates_users(client):
    await client.post("/notifications/send", json={
        "user_id": "user-A", "message": "Only for A",
        "notification_type": "BOOKING_CONFIRMED",
    })
    r = await client.get("/notifications/user/user-B")
    assert r.json() == []

@pytest.mark.asyncio
async def test_notification_has_required_fields(client):
    await client.post("/notifications/send", json={
        "user_id": "user-X", "message": "Test",
        "notification_type": "BOOKING_CANCELLED", "event_id": "evt-1",
    })
    n = (await client.get("/notifications/user/user-X")).json()[0]
    for field in ["notification_id","user_id","message","notification_type","timestamp","read"]:
        assert field in n