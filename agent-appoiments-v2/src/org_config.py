# src/org_config.py
"""
Organization configuration schema for multi-tenant appointment system.

Supports:
- Custom agent personalities
- Service management (max 10)
- Permission toggles
- Promotional offers
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, UUID4
from enum import Enum


DEFAULT_SYSTEM_PROMPT = """You are a professional appointment booking assistant.

Your role is to help clients:
- Schedule new appointments
- Reschedule existing appointments
- Cancel appointments when needed

Be courteous, efficient, and always verify information before confirming changes.
Ask one question at a time and guide users through the process step-by-step."""


class ServiceConfig(BaseModel):
    """Service configuration for an organization."""
    id: str = Field(..., description="Unique service ID (e.g., srv-001)")
    name: str = Field(..., min_length=1, max_length=100, description="Service name")
    description: str = Field(..., min_length=1, max_length=500, description="Service description")
    duration_minutes: int = Field(..., gt=0, le=480, description="Duration in minutes (1-480)")
    price: float = Field(..., ge=0, description="Price (0 or positive)")
    active: bool = Field(default=True, description="Whether service is active")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "srv-001",
                "name": "General Consultation",
                "description": "Standard medical consultation",
                "duration_minutes": 30,
                "price": 100.0,
                "active": True
            }
        }


class PermissionsConfig(BaseModel):
    """Permission toggles for agent capabilities."""
    can_book: bool = Field(default=True, description="Allow booking new appointments")
    can_reschedule: bool = Field(default=True, description="Allow rescheduling appointments")
    can_cancel: bool = Field(default=True, description="Allow canceling appointments")

    @validator('can_book', 'can_reschedule', 'can_cancel')
    def validate_at_least_one_permission(cls, v, values):
        """Ensure at least one permission is active after all fields validated."""
        return v

    @validator('can_cancel')
    def check_at_least_one_active(cls, v, values):
        """Check that at least one permission is True (runs after all fields set)."""
        if not v and not values.get('can_book') and not values.get('can_reschedule'):
            raise ValueError("At least one permission must be active")
        return v


class PromotionalOffer(BaseModel):
    """Flexible schema for promotional offers."""
    id: str = Field(..., description="Unique offer ID")
    title: str = Field(..., min_length=1, max_length=200, description="Offer title")
    description: str = Field(..., min_length=1, description="Offer description")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible metadata (service_id, discount, dates, etc.)"
    )
    active: bool = Field(default=True, description="Whether offer is active")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "offer-001",
                "title": "Spring Special - 20% Off",
                "description": "Get 20% off consultations during March",
                "metadata": {
                    "service_id": "srv-001",
                    "discount_percent": 20,
                    "valid_from": "2025-03-01",
                    "valid_until": "2025-03-31"
                },
                "active": True
            }
        }


class OrganizationConfig(BaseModel):
    """Complete organization configuration."""
    org_id: str = Field(..., description="Unique organization UUID")
    org_name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    system_prompt: Optional[str] = Field(
        None,
        max_length=4000,
        description="Custom system prompt (optional, uses default if None)"
    )
    services: List[ServiceConfig] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of services (1-10)"
    )
    permissions: PermissionsConfig = Field(
        default_factory=PermissionsConfig,
        description="Permission toggles"
    )
    promotional_offers: List[PromotionalOffer] = Field(
        default_factory=list,
        description="Optional promotional offers"
    )
    location: Optional[Dict[str, str]] = Field(
        default=None,
        description="Location information (name, address, city, phone)"
    )
    assigned_person: Optional[Dict[str, str]] = Field(
        default=None,
        description="Provider information (name, type, specialization)"
    )
    operating_hours: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Operating hours configuration"
    )

    @validator('services')
    def validate_service_count(cls, v):
        """Ensure max 10 services."""
        if len(v) > 10:
            raise ValueError("Maximum 10 services allowed")
        if len(v) < 1:
            raise ValueError("At least 1 service required")
        return v

    @validator('services')
    def validate_at_least_one_active_service(cls, v):
        """Ensure at least one service is active."""
        if not any(s.active for s in v):
            raise ValueError("At least one service must be active")
        return v

    def get_effective_system_prompt(self) -> str:
        """Get system prompt (custom or default)."""
        if self.system_prompt and self.system_prompt.strip():
            return self.system_prompt.strip()
        return DEFAULT_SYSTEM_PROMPT

    def get_active_services(self) -> List[ServiceConfig]:
        """Get only active services."""
        return [s for s in self.services if s.active]

    class Config:
        json_schema_extra = {
            "example": {
                "org_id": "550e8400-e29b-41d4-a716-446655440000",
                "org_name": "Downtown Medical Center",
                "system_prompt": None,
                "services": [
                    {
                        "id": "srv-001",
                        "name": "General Consultation",
                        "description": "Standard consultation",
                        "duration_minutes": 30,
                        "price": 100.0,
                        "active": True
                    }
                ],
                "permissions": {
                    "can_book": True,
                    "can_reschedule": True,
                    "can_cancel": True
                },
                "promotional_offers": []
            }
        }


def validate_organization_config(
    org_id: str,
    services: List[ServiceConfig],
    permissions: PermissionsConfig,
    **kwargs
) -> None:
    """
    Validate organization configuration parameters.

    Raises ValueError if validation fails.
    """
    if len(services) > 10:
        raise ValueError("Maximum 10 services allowed")
    if len(services) < 1:
        raise ValueError("At least 1 service required")
