# app/core/redis.py

import redis.asyncio as redis
from typing import Optional

from app.core.config import settings


class RedisClient:
    """Async Redis client wrapper"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis"""
        self._client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await self._client.ping()

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()

    @property
    def is_connected(self) -> bool:
        """Check if Redis client is connected"""
        return self._client is not None

    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    # Convenience methods
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        return await self.client.set(key, value, ex=ex, nx=nx)

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> redis.Redis:
    """Dependency to get Redis client"""
    return redis_client.client
