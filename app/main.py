import time
import uuid
from fastapi import FastAPI, Response, status
import asyncpg
import redis.asyncio as redis

app = FastAPI(title="inferenceAPI")

POSTGRES_URL = "postgresql://myuser:mypassword@localhost:5432/mydatabase"
REDIS_URL = "redis://localhost:6379/0"

@app.get("/health")
async def health_check(response: Response):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    db_status = "ok"
    redis_status = "ok"
    is_healthy = True

    # 1. Check PostgreSQL
    try:
        conn = await asyncpg.connect(POSTGRES_URL)
        await conn.execute("SELECT 1")
        await conn.close()
    except Exception:
        db_status = "error"
        is_healthy = False

    # 2. Check Redis
    try:
        r = redis.from_url(REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "error"
        is_healthy = False

    # 3. Calculate Latency
    latency_ms = int((time.time() - start_time) * 1000)

    # 4. Set HTTP Status Code for Kubernetes
    # If a dependency is down, AKS needs a non-200 status code to restart the pod.
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # 5. Return Enforced Standard Envelope
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