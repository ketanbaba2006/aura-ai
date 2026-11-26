/**
 * AURA AI Type Definitions
 */

// ─── Messages ────────────────────────────────────────────

export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  isStreaming?: boolean;
}

// ─── Conversations ───────────────────────────────────────

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  last_message?: string | null;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

// ─── Chat Events (SSE) ──────────────────────────────────

export interface ModelMetadata {
  provider: string;
  model: string;
  fallback?: boolean;
  fallback_from?: string;
  selection_source?: string;
}

export type ChatEventType =
  | "conversation_id"
  | "token"
  | "tool_use"
  | "tool_result"
  | "thinking"
  | "search"
  | "planner"
  | "agent_progress"
  | "done"
  | "error";

export interface ChatEvent {
  event: ChatEventType;
  data: {
    content: string;
    conversation_id?: string;
    metadata?: Record<string, unknown>;
    model?: ModelMetadata;
  };
}

// ─── Tools ───────────────────────────────────────────────

export interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolResult {
  success: boolean;
  output?: string;
  error?: string;
}

// ─── UI State ────────────────────────────────────────────

export interface ToolUsage {
  name: string;
  params?: Record<string, unknown>;
  result?: string;
  success?: boolean;
  isLoading: boolean;
}

export type AgentProgressStatus = "pending" | "running" | "completed" | "failed";

export interface AgentProgress {
  phase: "Planning" | "Generating Code" | "Testing" | "Fixing Errors" | "Deployment";
  status: AgentProgressStatus;
  detail: string;
  files?: string[];
  checks?: string[];
  attempt?: number;
  tasks?: { title: string; status: string }[];
}

// ─── Search ──────────────────────────────────────────────

export interface SearchResultItem {
  title: string;
  url: string;
  snippet: string;
  content: string;
  score: number;
  source_domain: string;
}

export interface MemorySearchResult {
  message_id: string;
  content: string;
  role: "user" | "assistant" | "system";
  relevance: number;
  created_at: string;
}

// ─── Modular Views ───────────────────────────────────────

export type ActiveView = "chat" | "agent" | "website-builder" | "app-builder" | "deep-research" | "projects" | "files" | "settings" | "notebook";
export type AuraState = 'idle' | 'thinking' | 'researching' | 'planning' | 'building' | 'deploying' | 'success' | 'error' | 'generating' | 'agent';
export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  children?: FileNode[];
}

export interface WorkspaceFileDetail {
  name: string;
  path: string;
  content: string;
  size: number;
  extension: string;
}

// ─── Activity Logs ────────────────────────────────────────

export interface ActivityLog {
  id: string;
  timestamp: string;
  action_type: string;
  category: string;
  description: string;
  details?: string | null;
  status: "success" | "error" | "info";
}

// ─── Goal Planner ────────────────────────────────────────

export interface Task {
  id: string;
  goal_id: string;
  title: string;
  description?: string | null;
  status: "pending" | "running" | "completed" | "failed";
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface Goal {
  id: string;
  title: string;
  description?: string | null;
  status: "pending" | "in_progress" | "completed";
  created_at: string;
  tasks?: Task[];
}

// ─── Knowledge Base ───────────────────────────────────────

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_size: number;
  upload_time: string;
  chunk_count: number;
}

export interface KnowledgeChunk {
  chunk_id: string;
  doc_id: string;
  filename: string;
  content: string;
  score: number;
}

// ─── Authentication ───────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
  role: "OWNER" | "ADMIN" | "USER";
  avatar_url?: string;
}

export interface AuthSession {
  id: string;
  device_info: string;
  ip_address: string;
  last_active: string;
  created_at: string;
  is_current: boolean;
}

// ─── Deep Research ────────────────────────────────────────

export type ResearchDepth = "quick" | "standard" | "deep" | "expert";

export interface ResearchSource {
  url: string;
  title: string;
  domain: string;
  trust_score: number;
  publication_date: string | null;
  category: "Research Paper" | "Document" | "Official Source" | "News Article" | "Web Article";
}

export interface ResearchProgressStep {
  id: string;
  label: string;
  status: "pending" | "running" | "completed";
}

export interface ResearchMetrics {
  current_step: string;
  current_source: string;
  pages_read: number;
  sources_found: number;
  facts_extracted: number;
  facts_verified: number;
  depth: string;
  elapsed_time: number;
}

export interface ResearchProgress {
  status: string;
  step: string;
  step_label: string;
  detail: string;
  metrics: ResearchMetrics;
  steps: ResearchProgressStep[];
}

export interface ResearchQuality {
  has_title: boolean;
  has_executive_summary: boolean;
  has_conclusion: boolean;
  has_sources: boolean;
  has_citations: boolean;
  citation_count: number;
  word_count: number;
  facts_count: number;
  quality_score: number;
  passed: boolean;
}

export interface ResearchReport {
  id: string;
  topic: string;
  depth: string;
  conversation_id: string;
  report_content?: string;
  markdown_path?: string;
  pdf_path?: string;
  docx_path?: string;
  sources?: ResearchSource[];
  quality?: ResearchQuality;
  elapsed_seconds?: number;
  facts_count?: number;
  sources_count?: number;
  created_at: string;
}

export interface ResearchSettings {
  research_provider: string;
  research_api_key: string;
  research_model: string;
  research_aws_region: string;
  research_temperature: string;
  research_depth: string;
  research_sources_limit: string;
  research_timeout: string;
}
