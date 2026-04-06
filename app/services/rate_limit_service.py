import time
import math
from typing import Tuple, Dict
from redis.asyncio import Redis
from app.core.rate_limits import get_limits_for_tier

LUA_RATE_LIMITER = """
local current_key = KEYS[1]
local previous_key = KEYS[2]
local limit = tonumber(ARGV[1])
local weight = tonumber(ARGV[2])
local expiry = tonumber(ARGV[3])

local current_count = tonumber(redis.call('GET', current_key) or "0")
local previous_count = tonumber(redis.call('GET', previous_key) or "0")

-- The Sliding Window Formula
local estimated_rate = (previous_count * weight) + current_count

if estimated_rate >= limit then
    return {0, math.ceil(estimated_rate)} -- Blocked
end

-- If allowed, increment the current window
local new_count = redis.call('INCR', current_key)
if new_count == 1 then
    redis.call('EXPIRE', current_key, expiry)
end

return {1, new_count} -- Allowed
"""

class RateLimitService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self._script = self.redis.register_script(LUA_RATE_LIMITER)

    async def is_rate_limited(self, tenant_id: str, tier: str) -> Tuple[bool, Dict[str, str]]:
        """
        Checks if a request is rate limited and returns the status.
        """
        limits = get_limits_for_tier(tier)
        limit = limits.requests_per_minute
        
        # Timing calculations
        now = time.time()
        current_window = int(now // 60)
        previous_window = current_window - 1
        
        seconds_into_minute = now % 60
        seconds_remaining = 60 - seconds_into_minute
        
        weight = seconds_remaining / 60
        
        current_key = f"rl:{tenant_id}:{current_window}"
        previous_key = f"rl:{tenant_id}:{previous_window}"
        
        allowed, count = await self._script(
            keys=[current_key, previous_key],
            args=[limit, weight, 120] 
        )
        
        is_limited = (allowed == 0)
        
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - count)),
            "X-RateLimit-Reset": str(int(now + seconds_remaining)), 
            "X-Retry-After": str(int(seconds_remaining))          
        }
        
        return is_limited, headers