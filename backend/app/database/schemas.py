"""
AURA AI Pydantic Schemas
Request/response models for the API.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatEventType(str, Enum):
    TOKEN = "token"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    SEARCH = "search"
    PLANNER = "planner"  # Added planner event
    AGENT_PROGRESS = "agent_progress"
    DONE = "done"
    ERROR = "error"


class LogStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"


# ─── Chat ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None
    conversationId: str | None = None
    provider: str | None = None
    model: str | None = None
    attachments: list[dict] = []
    autonomous: bool = False
    active_files: list[dict] = []
    timezone: str | None = None


class ChatEvent(BaseModel):
    event: ChatEventType
    data: str
    metadata: dict | None = None


# ─── Messages ─────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    metadata: dict | None = None
    created_at: datetime


# ─── Conversations ────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str = "New Conversation"


class ConversationUpdate(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: str | None = None


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []


# ─── Tools ────────────────────────────────────────────────

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: dict = {}
    permission_level: str = "safe"


class ToolExecuteRequest(BaseModel):
    params: dict = {}


class ToolResult(BaseModel):
    success: bool
    output: str | None = None
    error: str | None = None


# ─── Router ───────────────────────────────────────────────

class RouteDecision(BaseModel):
    needs_memory: bool = False
    needs_tool: bool = False
    tool_name: str | None = None
    tool_params: dict = {}
    needs_search: bool = False
    needs_planner: bool = False
    needs_knowledge: bool = False  # Control knowledge base lookup
    direct_response: bool = True
    reasoning: str = ""


# ─── Memory ───────────────────────────────────────────────

class MemorySearchResult(BaseModel):
    message_id: str
    content: str
    role: MessageRole
    relevance: float = 0.0
    created_at: datetime


# ─── Search ───────────────────────────────────────────────

class SearchResultItem(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    content: str = ""
    score: float = 0.0
    source_domain: str = ""
    provider: str = "Web"
    duplicates: list[dict] = []


class SearchResults(BaseModel):
    query: str
    results: list[SearchResultItem] = []
    summary: str = ""
    comparison: str = ""
    path_taken: list[str] = []
    cached: bool = False
    search_time: float = 0.0
    error: str | None = None


# ─── Activity Logs ────────────────────────────────────────

class ActivityLogCreate(BaseModel):
    action_type: str
    category: str
    description: str
    details: dict | None = None
    status: LogStatus = LogStatus.INFO


class ActivityLogResponse(BaseModel):
    id: str
    timestamp: datetime
    action_type: str
    category: str
    description: str
    details: str | None = None
    status: LogStatus


# ─── Planner Goals & Tasks ────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    order_index: int


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    order_index: int | None = None


class TaskResponse(BaseModel):
    id: str
    goal_id: str
    title: str
    description: str | None = None
    status: str
    order_index: int
    created_at: datetime
    updated_at: datetime


class GoalCreate(BaseModel):
    title: str
    description: str | None = None


class GoalResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: str
    created_at: datetime


class GoalDetailResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: str
    created_at: datetime
    tasks: list[TaskResponse] = []


# ─── Knowledge Base ───────────────────────────────────────

class KnowledgeChunkResponse(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeChunkResponse] = []
