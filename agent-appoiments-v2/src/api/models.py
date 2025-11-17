"""Pydantic models for API request/response validation."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator, UUID4, ConfigDict


class ChatRequest(BaseModel):
    """Request schema for /api/v1/chat endpoint."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message (1-2000 characters)",
        examples=["I'd like to book an appointment"]
    )
    session_id: UUID4 = Field(
        ...,
        description="Client session UUID for conversation tracking",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    org_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Organization identifier",
        examples=["org-123", "clinic-downtown"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "I need to book a consultation",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "org-123"
            }
        }
    )


class ChatResponse(BaseModel):
    """Response schema for /api/v1/chat endpoint."""
    response: str = Field(..., description="Agent response message")
    session_id: UUID4 = Field(..., description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata (state, context, etc.)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "I'd be happy to help! What service would you like?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {"current_state": "COLLECT_SERVICE"}
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Rate limit exceeded",
                "detail": "Maximum 100 requests per hour exceeded",
                "code": "RATE_LIMIT_EXCEEDED"
            }
        }
    )
