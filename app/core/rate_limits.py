from typing import Optional, Dict
from pydantic import BaseModel

class TierLimits(BaseModel):
    """
    Defines the throughput constraints for a specific service tier.
    """
    requests_per_minute: int
    requests_per_day: Optional[int]  
    max_concurrent: int

TIER_CONFIG: Dict[str, TierLimits] = {
    "free": TierLimits(
        requests_per_minute=10,
        requests_per_day=100,
        max_concurrent=2
    ),
    "pro": TierLimits(
        requests_per_minute=60,
        requests_per_day=10000,
        max_concurrent=10
    ),
    "enterprise": TierLimits(
        requests_per_minute=600,
        requests_per_day=None, 
        max_concurrent=50
    ),
}

def get_limits_for_tier(tier: str) -> TierLimits:
    """
    Helper to fetch limits, defaults to 'free' if a tier is unknown.
    """
    tier_str = tier.value if hasattr(tier, "value") else str(tier)
    
    return TIER_CONFIG.get(tier_str.lower(), TIER_CONFIG["free"])