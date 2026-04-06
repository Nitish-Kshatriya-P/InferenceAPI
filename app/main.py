import time
import os
import uuid
import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, Response, status
from app.api.v1 import tenants, api_keys
from dotenv import load_dotenv
from app.api.v1 import rate_limits
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from app.api.v1 import inference
from fastapi.exception_handlers import http_exception_handler

load_dotenv()

POSTGRES_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

app = FastAPI(title="inferenceAPI")

app.include_router(
    tenants.router, 
    prefix = "/api/v1"
)
app.include_router(
    api_keys.router, 
    prefix= "/api/v1"
)
app.include_router(
    rate_limits.router, 
    prefix="/api/v1/rate-limits", 
    tags=["Rate Limits"]
)
app.include_router(
    inference.router, 
    prefix="/api/v1/inference", 
    tags=["AI Inference"]
)

@app.get("/health")
async def health_check(response: Response):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    db_status = "ok"
    redis_status = "ok"
    is_healthy = True

    try:
        conn = await asyncpg.connect(POSTGRES_URL)
        await conn.execute("SELECT 1")
        await conn.close()
    except Exception:
        db_status = "error"
        is_healthy = False

    try:
        r = redis.from_url(REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "error"
        is_healthy = False

    latency_ms = int((time.time() - start_time) * 1000)

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "success" if is_healthy else "error",
        "data": {
            "db": db_status,
            "redis": redis_status
        },
        "meta": {
            "request_id": request_id,
            "latency_ms": latency_ms
        }
    }

@app.exception_handler(HTTPException)
async def custom_429_handler(request, exc: HTTPException):
    if exc.status_code == 429:
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "data": exc.detail 
            },
            headers=exc.headers
        )
    return await http_exception_handler(request, exc)