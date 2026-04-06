import asyncio
import httpx
import os
import time
import json
from dotenv import load_dotenv
from typing import Any, Dict, Optional, AsyncGenerator
from fastapi import HTTPException, status
from app.core.model_registry import get_model_info

# Load environment variables
load_dotenv()

class ModelRouterService:
    def __init__(self):
        timeout = httpx.Timeout(30.0, connect=5.0) 
        self.client = httpx.AsyncClient(timeout=timeout)

    async def route_inference(
        self, 
        task_type: str, 
        payload: Dict[str, Any], 
        stream: bool = False
    ) -> Any:
        """
        Coordinates the lookup, retry logic, and execution of a model request.
        """
        model_meta = get_model_info(task_type)
        if not model_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model task '{task_type}' is not supported by inferenceAPI."
            )

        # Grab the token safely
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_token:
            raise HTTPException(status_code=500, detail="HF TOKEN environment variable is missing.")

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.post(
                    model_meta.endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {hf_token}"},
                    timeout=model_meta.timeout_seconds
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code in [503, 429] and attempt < max_retries:
                    wait_time = 2 ** attempt 
                    print(f"[{task_type}] Received {response.status_code}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()

            except httpx.HTTPStatusError as e:
                if attempt == max_retries:
                    raise HTTPException(
                        status_code=e.response.status_code,
                        detail=f"Provider Error: {e.response.text}"
                    )
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="The model provider took too long to respond."
                )

        raise HTTPException(
            status_code=503, 
            detail="Model is currently unavailable after multiple retries."
        )

    async def shutdown(self):
        """Cleanup connection pool on app shutdown."""
        await self.client.aclose()

    async def stream_inference(
        self, 
        task_type: str, 
        payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Streams raw chunks from the provider as an AsyncGenerator.
        """
        model_meta = get_model_info(task_type)
        if not model_meta or not model_meta.supports_streaming:
            raise ValueError(f"Streaming not supported for {task_type}")

        # Grab the token safely here too!
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise HTTPException(status_code=500, detail="HF_TOKEN environment variable is missing.")

        payload["stream"] = True 

        async with self.client.stream(
            "POST",
            model_meta.endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {hf_token}"},
            timeout=model_meta.timeout_seconds
        ) as response:
            if response.status_code != 200:
                yield json.dumps({"error": "Provider stream failed"})
                return

            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    yield data_str

