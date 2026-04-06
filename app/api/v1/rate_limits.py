from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from app.core.dependencies import verify_rate_limit
from app.models.tenant import Tenant
from app.core.database import get_redis
from app.services.rate_limit_service import RateLimitService
from redis.asyncio import Redis

router = APIRouter()

@router.get("/status")
async def get_rate_limit_status(
    auth_data: dict = Depends(verify_rate_limit) 
):
    current_tenant = auth_data["tenant"]
    headers = auth_data["rate_limit_data"]
    
    reset_timestamp = int(headers["X-RateLimit-Reset"])
    reset_iso = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc).isoformat()

    return {
        "status": "success",
        "data": {
            "tier": current_tenant.tier,
            "window": "60s",
            "limit": int(headers["X-RateLimit-Limit"]),
            "used": int(headers["X-RateLimit-Limit"]) - int(headers["X-RateLimit-Remaining"]),
            "remaining": int(headers["X-RateLimit-Remaining"]),
            "reset_at": reset_iso
        }
    }