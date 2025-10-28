import os
import asyncio
import aiofiles
from typing import Optional

class DistributedQueue:
    def __init__(self, node_id, redis_client=None):
        self.node_id = node_id
        self.redis = redis_client
        self._lock = asyncio.Lock()

    async def produce(self, topic: str, message: str):
        """Produce message to queue with error handling"""
        key = f"queue:{topic}"
        try:
            if self.redis:
                await self.redis.rpush(key, message)
            else:
                await self._produce_to_file(topic, message)
        except Exception as e:
            print(f"Error producing message to {topic}: {e}")
            raise

    async def consume(self, topic: str) -> Optional[str]:
        """Consume message from queue with error handling"""
        key = f"queue:{topic}"
        try:
            if self.redis:
                item = await self.redis.lpop(key)
                return item if item else None
            else:
                return await self._consume_from_file(topic)
        except Exception as e:
            print(f"Error consuming message from {topic}: {e}")
            return None

    async def _produce_to_file(self, topic: str, message: str):
        """Produce message to file (fallback mode)"""
        p = f"/tmp/{topic}.queue"
        async with self._lock:
            async with aiofiles.open(p, "a", encoding='utf-8') as f:
                await f.write(message + "\n")

    async def _consume_from_file(self, topic: str) -> Optional[str]:
        """Consume message from file (fallback mode)"""
        p = f"/tmp/{topic}.queue"
        if not os.path.exists(p):
            return None
        
        async with self._lock:
            async with aiofiles.open(p, "r", encoding='utf-8') as f:
                lines = await f.readlines()
            
            if not lines:
                return None
            
            first = lines[0].strip()
            
            async with aiofiles.open(p, "w", encoding='utf-8') as f:
                await f.writelines(lines[1:])
            
            return first

    async def get_queue_length(self, topic: str) -> int:
        """Get current queue length"""
        key = f"queue:{topic}"
        try:
            if self.redis:
                return await self.redis.llen(key)
            else:
                p = f"/tmp/{topic}.queue"
                if not os.path.exists(p):
                    return 0
                async with aiofiles.open(p, "r", encoding='utf-8') as f:
                    lines = await f.readlines()
                return len(lines)
        except Exception as e:
            print(f"Error getting queue length for {topic}: {e}")
            return 0
