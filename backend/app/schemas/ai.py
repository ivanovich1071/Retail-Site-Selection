from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    answer: str
    tool_trace: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str
    model: Optional[str] = None
    intent: Optional[str] = None
    llm_error: Optional[str] = None


class ActionRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)


class ActionResponse(BaseModel):
    ok: bool
    tool: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_ms: Optional[float] = None
