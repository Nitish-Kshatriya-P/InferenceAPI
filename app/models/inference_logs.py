import uuid
import enum
from sqlalchemy import Column, String, Integer, Enum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.models.base import AbstractBase  

class ProtocolEnum(str, enum.Enum):
    http = "http"
    ws = "ws"
    grpc = "grpc"

class StatusEnum(str, enum.Enum):
    success = "success"
    error = "error"
    timeout = "timeout"

class InferenceLog(AbstractBase):
    __tablename__ = "inference_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foriegn key to your tenants table
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    model_name = Column(String, nullable=False, index=True)
    protocol = Column(Enum(ProtocolEnum), nullable=False)
    
    # Billing metrics
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    
    # Performance metrics
    latency_ms = Column(Integer, nullable=False)
    
    # Status and Debugging
    status = Column(Enum(StatusEnum), nullable=False, index=True)
    error_message = Column(String, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)