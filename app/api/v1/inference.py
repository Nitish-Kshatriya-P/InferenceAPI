import io
import asyncio
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response, status
from app.core.dependencies import verify_rate_limit
from fastapi.responses import StreamingResponse
from app.services.model_router import ModelRouterService
from app.models.tenant import Tenant
from app.core.database import get_redis
from app.services.queue_service import QueueService
from redis.asyncio import Redis
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession 
from app.core.model_registry import get_model_info

router = APIRouter()
model_router = ModelRouterService()

@router.post("/chat")
async def chat_inference(
    payload: dict,
    auth_data: dict = Depends(verify_rate_limit), 
    redis: Redis = Depends(get_redis)
):
    """
    Accepts an inference request, prioritizes it, and queues it for the workers.
    """
    queue_svc = QueueService(redis)
    
    queue_name = await queue_svc.enqueue_request(
        tenant_id=str(auth_data["tenant.id"]),
        tier=auth_data["tenant.tier"],
        payload=payload
    )
    
    return {
        "status": "accepted",
        "message": f"Request queued in {queue_name}",
        "tier": auth_data["tenant.tier"]
    }

@router.post("/text")
async def generate_text(
    payload: dict,
    auth_data: dict = Depends(verify_rate_limit)
):
    """
    Standard Text Generation endpoint using the OpenAI standard.
    """

    model_meta = get_model_info("text-generation")
    if not model_meta:
         raise HTTPException(status_code=404, detail="Model task not found.")

    hf_payload = {
        "model": model_meta.model_id, 
        "messages": [
            {"role": "user", "content": payload.get("prompt", "")}
        ],
        "max_tokens": payload.get("max_tokens", 256)
    }
    
    result = await model_router.route_inference(
        task_type="text-generation",
        payload=hf_payload
    )
    
    extracted_text = "Error extracting text."
    if "choices" in result and len(result["choices"]) > 0:
        extracted_text = result["choices"][0].get("message", {}).get("content", "")
    
    return {
        "status": "success",
        "data": {
            "generated_text": extracted_text
        }
    }

@router.post("/speech-to-text")
async def transcribe_audio(
    file: UploadFile = File(...),
    auth_data: dict = Depends(verify_rate_limit)
):
    """
    Accepts binary audio and returns a transcript.
    """
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file too large (Max 10MB)")

    audio_bytes = await file.read()
    
    result = await model_router.route_inference(
        task_type="speech-to-text",
        payload={"inputs": audio_bytes} 
    )
    
    return {
        "status": "success",
        "data": result
    }

@router.post("/text-to-speech")
async def synthesize_speech(
    payload: dict,
    auth_data: dict = Depends(verify_rate_limit)
):
    """
    Accepts text and returns binary audio/wav data.
    """
    if "text" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'text' field in payload")

    audio_content = await model_router.route_inference(
        task_type="text-to-speech",
        payload=payload
    )
    
    return Response(
        content=audio_content,
        media_type="audio/wav"
    )

@router.websocket("/stream")
async def websocket_inference(
    websocket: WebSocket,
    token: str = Query(...), 
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    await websocket.accept()
    
    try:
        from app.core.dependencies import get_current_tenant
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        from fastapi import BackgroundTasks
        tenant = await get_current_tenant(BackgroundTasks(), creds, redis, db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        data = await websocket.receive_json()
        task_type = data.get("model", "text-generation")
        prompt = data.get("prompt")

        token_queue = asyncio.Queue(maxsize=20)

        async def producer():
            async for chunk_str in model_router.stream_inference(task_type, {"inputs": prompt}):
                chunk = json.loads(chunk_str)
                token_text = chunk.get("token", {}).get("text", "")
                await token_queue.put({"token": token_text, "done": False})
            
            await token_queue.put({"token": "", "done": True, "usage": {"status": "complete"}})

        producer_task = asyncio.create_task(producer())

        while True:
            message = await token_queue.get()
            
            await websocket.send_json(message)
            
            if message.get("done"):
                break

        await producer_task

    except WebSocketDisconnect:
        print(f"Client disconnected from stream: {tenant.id}")
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        if not websocket.client_state.name == "DISCONNECTED":
            await websocket.close()