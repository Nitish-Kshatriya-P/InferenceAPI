import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.tenant import TierEnum


class TenantCreate(BaseModel):
    """Payload for creating a new Tenant."""
    name: str
    email: EmailStr
    tier: TierEnum = TierEnum.free


class TenantResponse(BaseModel):
    """Payload for returning Tenant data."""
    id: uuid.UUID
    name: str
    email: EmailStr
    tier: TierEnum
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)