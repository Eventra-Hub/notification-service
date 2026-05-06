from redis.asyncio import Redis, from_url
from app.core.config import settings

client: Redis | None = None

async def connect_redis():
    global client
    client = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await client.ping()

async def close_redis():
    global client
    if client:
        await client.aclose()
        client = None
