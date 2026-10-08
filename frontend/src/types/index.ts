import { UseMutationResult } from "@tanstack/react-query";

// Chat types
export interface Message {
  id: number;
  content: string;
  role: 'user' | 'assistant';
  model_used?: string;
  tokens_used?: number;
  response_time?: number;
  created_at: string;
  timestamp?: Date;
  sources?: DocumentSource[];
}

export interface Conversation {
  id: number;
  title?: string;
  created_at: string;
  updated_at?: string;
  is_active: boolean;
  message_count: number;
  messages?: Message[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: number;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  use_context?: boolean;
  document_ids?: number[];
}

export interface ChatResponse {
  message: string;
  conversation_id: number;
  model_used: string;
  tokens_used?: number;
  response_time?: number;
  context_used?: boolean;
  sources?: DocumentSource[];
  rag_fallback?: boolean;
}

export interface DocumentSource {
  id: number; // matches [n] citation number
  document_id: number;
  document_title: string;
  similarity_score: number;
}

// Document types
export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  uploaded_at: string;
  processed: boolean;
  processed_at?: string;
  chunk_count: number;
  title?: string;
  description?: string;
}

export interface DocumentUpload {
  title?: string;
  description?: string;
  keywords?: string;
}

export interface DocumentSearchRequest {
  query: string;
  limit?: number;
  similarity_threshold?: number;
  document_ids?: number[];
}

export interface DocumentSearchResult {
  document_id: number;
  document_title: string;
  chunk_content: string;
  similarity_score: number;
  metadata?: Record<string, any>;
}

// Model types
export interface ModelInfo {
  name: string;
  provider: 'openai' | 'local' | 'huggingface';
  description: string;
  context_length: number;
  cost_per_token: number;
  status?: 'available' | 'unavailable' | 'mock';
}

export interface ModelConfig {
  name: string;
  provider: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

// API Response types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  database_status: string;
  models_available: string[];
}

// UI State types
export interface ChatState {
  conversations: Conversation[];
  currentConversation?: Conversation;
  messages: Message[];
  isLoading: boolean;
  isTyping: boolean;
  error?: string;
}

export interface DocumentState {
  documents: Document[];
  isUploading: boolean;
  isProcessing: boolean;
  error?: string;
}

export interface AppState {
  chat: ChatState;
  documents: DocumentState;
  selectedModel: string;
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
}

// Component Props types
export interface MessageProps {
  message: Message;
  isLast?: boolean;
}

export interface ChatInputProps {
  input: string;
  setInput: (input: string) => void;
  handleKeyPress: (e: React.KeyboardEvent) => void;
  handleSendMessage: () => void;
  sendMessageMutation: UseMutationResult<ChatResponse, unknown, ChatRequest, void>;
  selectedModel: string;
  inputRef: React.RefObject<HTMLTextAreaElement>;
}

export interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  conversations: Conversation[];
  onConversationSelect: (conversation: Conversation) => void;
  currentConversationId?: number;
  onConversationDelete: (conversationId: number) => void;
}

export interface DocumentUploadProps {
  onUpload: (file: File, metadata: DocumentUpload) => void;
  isUploading?: boolean;
}

export interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModel: string;
  onModelChange: (model: string) => void;
}

// Form types
export interface DocumentUploadForm {
  title: string;
  description: string;
  keywords: string;
}

export interface ChatSettings {
  model: string;
  temperature: number;
  max_tokens: number;
  use_context: boolean;
  selected_documents: number[];
}

// Utility types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export interface SearchParams extends PaginationParams {
  query?: string;
  processed_only?: boolean;
} 

// Auth types
export interface TokenResponse {
  access_token: string;
  token_type: string;
}