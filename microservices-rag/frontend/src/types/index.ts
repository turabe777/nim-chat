export interface Document {
  document_id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  metadata?: Record<string, any>;
}

export interface DocumentUploadResponse {
  success: boolean;
  document_id: string;
  filename: string;
  file_size: number;
  upload_time: number;
}

export interface TextChunk {
  chunk_id: string;
  content: string;
  chunk_index: number;
  start_position: number;
  end_position: number;
  metadata?: Record<string, any>;
}

export interface QuestionAnsweringRequest {
  question: string;
  document_id: string;
  context_length?: number;
  similarity_threshold?: number;
  model?: string;
  max_tokens?: number;
  temperature?: number;
}

export interface ContextItem {
  chunk_id: string;
  content: string;
  similarity_score: number;
}

export interface QuestionAnsweringResponse {
  success: boolean;
  question: string;
  answer: string;
  confidence: number;
  contexts_used: ContextItem[];
  total_contexts_found: number;
  model_used: string;
  processing_time: number;
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface ApiError {
  detail: string;
  error_code: string;
  timestamp: string;
  service: string;
}

export interface ServiceStatus {
  name: string;
  port: number;
  status: 'healthy' | 'unhealthy' | 'loading';
  url: string;
}