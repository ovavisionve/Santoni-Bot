from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: int | None = None
    file_id: str | None = None
    agent_name: str | None = None


class ChatResponse(BaseModel):
    message: str
    message_id: int
    conversation_id: int
    agent_used: str | None = None
    metadata: dict | None = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    agent_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}
