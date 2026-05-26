"""
Pydantic models for AI Agent Platform & Sandbox.
Defines the data structures for agent reasoning, tool execution, and traces.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"
    CONTEXT_UPDATE = "context_update"


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class ToolSchema(BaseModel):
    name: str
    description: str
    category: str = "general"
    parameters: list[ToolParameter] = []
    examples: list[str] = []


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


class AgentStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_number: int
    step_type: StepType
    content: str
    tool_call: Optional[ToolCall] = None
    tool_result: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float = 0
    tokens_used: int = 0
    metadata: dict[str, Any] = {}


class LLMConfig(BaseModel):
    provider: str = "pollinations"  # "pollinations", "openai", "gemini", "claude"
    api_key: Optional[str] = None
    model: Optional[str] = None


class AgentRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    max_steps: int = 10
    temperature: float = 0.7
    llm_config: Optional[LLMConfig] = None



class AgentResponse(BaseModel):
    conversation_id: str
    steps: list[AgentStep]
    final_answer: str
    total_tokens: int
    total_latency_ms: float


class SSEEvent(BaseModel):
    event_type: str  # "step", "done", "error"
    data: dict[str, Any]


class ConversationMessage(BaseModel):
    role: str  # "user", "agent"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    steps: list[AgentStep] = []


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[ConversationMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    context_tokens: int = 0
    metadata: dict[str, Any] = {}


class TraceEntry(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    step: AgentStep
    parent_trace_id: Optional[str] = None


class ContextWindow(BaseModel):
    max_tokens: int = 4096
    current_tokens: int = 0
    messages: list[ConversationMessage] = []
    summary: Optional[str] = None
