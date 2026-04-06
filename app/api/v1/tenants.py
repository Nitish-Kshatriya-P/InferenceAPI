from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse
from app.core.dependencies import verify_rate_limit
from app.core.database import get_db  

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    tenant_in: TenantCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new tenant. 
    """
    new_tenant = Tenant(
        name=tenant_in.name,
        email=tenant_in.email,
        tier=tenant_in.tier
    )
    
    db.add(new_tenant)
    try:
        await db.commit()
        await db.refresh(new_tenant)
        return new_tenant
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tenant with this email already exists."
        )

@router.get("/me", response_model=TenantResponse)
async def get_current_tenant_profile(
    auth_data: dict = Depends(verify_rate_limit) 
):
    return auth_data["tenant"]