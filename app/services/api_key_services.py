import base64
import secrets
import uuid
from passlib.context import CryptContext

from sqlalchemy.ext.asyncio import AsyncSession 

from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyCreateResponse

# Initialize the bcrypt hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_api_key(
    db: AsyncSession, 
    tenant_id: uuid.UUID, 
    key_in: APIKeyCreate
) -> APIKeyCreateResponse:
    
    # Generate 32 cryptographically random bytes
    random_bytes = secrets.token_bytes(32)
    
    # Encode as URL-safe base64 string 
    encoded_string = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip("=")
    
    # Prepend prefix
    raw_full_key = f"lapi_sk_{encoded_string}"
    
    key_prefix = raw_full_key[:16]

    key_hash = pwd_context.hash(raw_full_key)
    
    db_api_key = APIKey(
        tenant_id=tenant_id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=key_in.name,
        expires_at=key_in.expires_at
    )
    
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)
    
    # Return full raw key ONCE to the caller
    return APIKeyCreateResponse(
        id=db_api_key.id,
        name=db_api_key.name,
        key_prefix=db_api_key.key_prefix,
        raw_key=raw_full_key, 
        created_at=db_api_key.created_at
    )