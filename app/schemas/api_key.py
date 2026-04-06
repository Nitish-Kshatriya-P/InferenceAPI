import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreate(BaseModel):
    """Payload for requesting a new API Key."""
    name: str = Field(..., max_length=100, description="Human readable name for the key")
    expires_at: Optional[datetime] = None


class APIKeyCreateResponse(BaseModel):
    """
    Payload for returning only once to show the raw_key after creating it.
    """
    id: uuid.UUID
    name: str
    key_prefix: str
    raw_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyResponse(BaseModel):
    """
    Standard payload for returning API Key details. (Excludes raw_key and key_hash)
    """
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)