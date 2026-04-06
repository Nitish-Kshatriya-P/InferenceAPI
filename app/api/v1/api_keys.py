import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse
from app.core.dependencies import get_current_tenant
from app.services.api_key_services import create_api_key
from app.core.database import get_db, get_redis 

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key(
    key_in: APIKeyCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new API key for the authenticated tenant.
    The raw key will only be returned once.
    """
    return await create_api_key(db=db, tenant_id=current_tenant.id, key_in=key_in)


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    List all API keys belonging to the authenticated tenant.
    Hashes and raw keys are strictly excluded by the response schema.
    """
    stmt = select(APIKey).where(APIKey.tenant_id == current_tenant.id)
    result = await db.execute(stmt)
    keys = result.scalars().all()
    
    return keys


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """
    Immediately revoke an API key.
    Instead of hard-deleting, we set is_active to False to maintain an audit trail.
    """
    stmt = select(APIKey).where(
        APIKey.id == key_id, 
        APIKey.tenant_id == current_tenant.id
    )
    result = await db.execute(stmt)
    db_key = result.scalar_one_or_none()

    if not db_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="API Key not found"
        )

    # Soft delete
    db_key.is_active = False
    await db.commit()
    
    cache_key = f"auth:{db_key.key_prefix}"
    await redis_client.delete(cache_key)
    
    return None