import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.api_key_services import create_api_key
from app.schemas.api_key import APIKeyCreate

# --- ADD THESE TWO LINES ---
from app.models.tenant import Tenant
from app.models.api_key import APIKey
# ---------------------------

DATABASE_URL = "postgresql+asyncpg://myuser:mypassword@localhost:5432/mydatabase"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed():
    tenant_id_string = "c902aedd-0ab6-42ad-93e7-8a05aaf0f7a7" 
    
    tenant_id = uuid.UUID(tenant_id_string) 
    
    async with AsyncSessionLocal() as db:
        key_schema = APIKeyCreate(name="Bootstrap Admin Key")
        
        result = await create_api_key(db, tenant_id, key_schema)
        
        print("\n" + "="*50)
        print(f"SUCCESS! Your raw API key is:")
        print(f"{result.raw_key}")
        print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(seed())