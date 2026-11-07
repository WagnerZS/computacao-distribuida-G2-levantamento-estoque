import json
from typing import Any

from redis.asyncio import Redis


class RedisCache:
    def __init__(self, redis: Redis, ttl_seconds: int = 30) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get_json(self, key: str, version: str) -> Any | None:
        try:
            cached = await self._redis.get(key)
            if not cached:
                return None
            value = json.loads(str(cached))
            return value.get("payload") if value.get("version") == version else None
        except Exception:
            return None

    async def set_json(self, key: str, version: str, payload: Any) -> None:
        try:
            await self._redis.set(
                key,
                json.dumps({"version": version, "payload": payload}, ensure_ascii=False),
                ex=self._ttl_seconds,
            )
        except Exception:
            pass

    async def delete(self, *keys: str) -> None:
        try:
            await self._redis.delete(*keys)
        except Exception:
            pass

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False
