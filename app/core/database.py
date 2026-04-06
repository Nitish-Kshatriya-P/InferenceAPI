import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()
POSTGRES_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

engine = create_async_engine(POSTGRES_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session and safely closes it after the request finishes."""
    async with AsyncSessionLocal() as session:
        yield session
        
async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Yields a Redis client and safely closes it after the request finishes."""
    client = redis.from_url(REDIS_URL)
    try:
        yield client
    finally:
        await client.aclose()