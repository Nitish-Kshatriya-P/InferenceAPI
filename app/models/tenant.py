import enum
from sqlalchemy import String, Boolean, Enum, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AbstractBase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.api_key import APIKey


class TierEnum(enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class Tenant(AbstractBase):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    tier: Mapped[TierEnum] = mapped_column(Enum(TierEnum), default=TierEnum.free, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'), nullable=False)
    
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", 
        back_populates="tenant", 
        cascade="all, delete-orphan"
    )