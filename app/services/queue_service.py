import json
from redis.asyncio import Redis
from typing import Any, Dict

class QueueService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.queue_map = {
            "enterprise": "queue:enterprise",
            "pro": "queue:pro",
            "free": "queue:free"
        }

    async def enqueue_request(self, tenant_id: str, tier: str, payload: Dict[str, Any]) -> str:
        """
        Pushes a request into the appropriate priority queue.
        """

        queue_name = self.queue_map.get(tier.lower(), "queue:free")
        
        job_data = {
            "tenant_id": tenant_id,
            "tier": tier,
            "payload": payload,
            "enqueued_at": json.dumps(payload.get("timestamp", "")) 
        }
        
        await self.redis.lpush(queue_name, json.dumps(job_data))
        
        return queue_name