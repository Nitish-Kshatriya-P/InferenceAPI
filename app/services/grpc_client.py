import grpc
import time
from typing import Any, Dict
from app.grpc import inference_pb2, inference_pb2_grpc

class GRPCInferenceClient:
    def __init__(self, host: str = "localhost", port: int = 50051):
        self.target = f"{host}:{port}"
        self.channel = grpc.aio.insecure_channel(self.target)
        self.stub = inference_pb2_grpc.InferenceServiceStub(self.channel)

    async def get_inference(
        self, 
        model_name: str, 
        prompt: str, 
        tenant_id: str, 
        max_tokens: int = 256
    ) -> Dict[str, Any]:
        """
        Sends a one-shot request to the internal worker.
        """
        request = inference_pb2.InferenceRequest(
            model_name=model_name,
            prompt=prompt,
            max_tokens=max_tokens,
            tenant_id=tenant_id
        )

        try:
            start_time = time.time()
            response = await self.stub.Infer(request, timeout=10.0)
            end_time = time.time()

            return {
                "text": response.generated_text,
                "usage": response.tokens_used,
                "latency_ms": response.latency_ms,
                "request_id": response.request_id,
                "internal_rtt_ms": (end_time - start_time) * 1000
            }

        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()} - {e.details()}")
            return {"error": "Internal worker unavailable", "code": str(e.code())}

    async def close(self):
        """Close the channel connection."""
        await self.channel.close()