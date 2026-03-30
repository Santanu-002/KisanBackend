from redis.asyncio import Redis
from kisan_backend.core.config import settings

def get_redis_client() -> Redis:
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )

async def get_redis() -> Redis:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.close()
