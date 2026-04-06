import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict

from fastapi import Depends, HTTPException, status, BackgroundTasks, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from redis.asyncio import Redis

from app.core.security import verify_api_key
from app.models.api_key import APIKey
from app.models.tenant import Tenant
from app.core.database import get_db, get_redis
from app.services.rate_limit_service import RateLimitService

security = HTTPBearer()

async def update_key_last_used(db: AsyncSession, api_key_id: uuid.UUID):
    """Background task for updating the timestamp without delaying the API response."""
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key_id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def get_current_tenant(
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis_client: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    The main auth dependency. Protects routes by validating the API Key & implements a secure SHA-256 Redis caching strategy.
    """
    token = credentials.credentials
    
    if not token.startswith("lapi_sk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid API Key format"
        )
        
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    cache_key = f"auth:{token_hash}"
    
    cached_tenant_id = await redis_client.get(cache_key)
    
    if cached_tenant_id:
        tenant_uuid = uuid.UUID(cached_tenant_id.decode('utf-8'))
        tenant = await db.get(Tenant, tenant_uuid)
        
        if not tenant or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Tenant is inactive or deleted"
            )
        return tenant

    key_prefix = token[:16]
    stmt = (
        select(APIKey)
        .where(APIKey.key_prefix == key_prefix)
        .options(joinedload(APIKey.tenant))
    )
    result = await db.execute(stmt)
    db_api_key = result.scalar_one_or_none()

    if not db_api_key or not db_api_key.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
        
    if not db_api_key.tenant.is_active:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant is inactive")

    if not verify_api_key(token, db_api_key.key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

    background_tasks.add_task(update_key_last_used, db, db_api_key.id)
    
    await redis_client.setex(cache_key, 300, str(db_api_key.tenant_id))

    return db_api_key.tenant


async def verify_rate_limit(
    response: Response,
    tenant: Tenant = Depends(get_current_tenant),
    redis: Redis = Depends(get_redis)
) -> dict: 
    limiter = RateLimitService(redis)
    is_limited, headers = await limiter.is_rate_limited(str(tenant.id), tenant.tier)

    for key, value in headers.items():
        if key != "X-Retry-After":
            response.headers[key] = str(value)

    if is_limited:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Try again in {headers['X-Retry-After']} seconds.",
                "retry_after": int(headers["X-Retry-After"])
            },
            headers={
                **headers, 
                "Retry-After": headers["X-Retry-After"]
            }
        )

    return {
        "tenant": tenant,
        "rate_limit_data": headers
    }