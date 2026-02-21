"""
Pydantic schemas for API request/response models.
"""
from pydantic import BaseModel
from typing import Optional, List


class SessionInitResponse(BaseModel):
    session_id: str
    message: str = "Session created"


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str = "general_enquiry"
    lead_status: str = "NOT_STARTED"
    quick_replies: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    kb_document_count: int
    kb_ready: bool


class ScrapeRequest(BaseModel):
    pass


class ScrapeResponse(BaseModel):
    status: str
    message: str
