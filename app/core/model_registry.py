from typing import Dict, Optional
from pydantic import BaseModel, HttpUrl

class ModelMetadata(BaseModel):
    """
    Schema for model configuration.Ensures every model added follows the same contract.
    """
    provider: str
    model_id: str
    endpoint: str
    supports_streaming: bool = False
    max_tokens: Optional[int] = None
    timeout_seconds: int = 30

MODEL_REGISTRY: Dict[str, ModelMetadata] = {
    "text-generation": ModelMetadata(
        provider="huggingface",
        model_id="Qwen/Qwen2.5-7B-Instruct", 
        endpoint="https://router.huggingface.co/v1/chat/completions", 
        supports_streaming=True, 
        max_tokens=2048,
        timeout_seconds=30
    ),
    "speech-to-text": ModelMetadata(
        provider="huggingface",
        model_id="openai/whisper-large-v3",
        endpoint="https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3",
        supports_streaming=False,
        timeout_seconds=60
    ),
    "text-to-speech": ModelMetadata(
        provider="huggingface",
        model_id="facebook/mms-tts-eng",
        endpoint="https://router.huggingface.co/hf-inference/models/facebook/mms-tts-eng",
        supports_streaming=False,
        timeout_seconds=45
    )
}

def get_model_info(task_type: str) -> Optional[ModelMetadata]:
    """
    Helper to safely retrieve model metadata by task type.
    """
    return MODEL_REGISTRY.get(task_type.lower())