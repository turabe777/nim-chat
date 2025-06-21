import axios from 'axios';
import { 
  Document, 
  DocumentUploadResponse, 
  QuestionAnsweringRequest, 
  QuestionAnsweringResponse,
  HealthStatus,
  ServiceStatus
} from '@/types';

// Base API configuration
// const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '';

// Service endpoints
const SERVICES = {
  DOCUMENT: 'http://localhost:8001',
  TEXT_PROCESSING: 'http://localhost:8002', 
  EMBEDDING: 'http://localhost:8003',
  VECTOR_STORE: 'http://localhost:8004',
  LLM: 'http://localhost:8005'
};

// Create axios instances for each service
const createApiClient = (baseURL: string) => {
  return axios.create({
    baseURL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

export const documentApi = createApiClient(SERVICES.DOCUMENT);
export const textProcessingApi = createApiClient(SERVICES.TEXT_PROCESSING);
export const embeddingApi = createApiClient(SERVICES.EMBEDDING);
export const vectorStoreApi = createApiClient(SERVICES.VECTOR_STORE);
export const llmApi = createApiClient(SERVICES.LLM);

// Document Service APIs
export const documentService = {
  upload: async (files: FileList, documentName?: string): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    
    // Add files to form data
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });
    
    if (documentName) {
      formData.append('document_name', documentName);
    }

    const response = await documentApi.post<DocumentUploadResponse>(
      '/api/v1/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    
    return response.data;
  },

  getDocument: async (documentId: string): Promise<Document> => {
    const response = await documentApi.get<Document>(`/api/v1/documents/${documentId}`);
    return response.data;
  },

  getDocuments: async (): Promise<Document[]> => {
    // Note: This endpoint might not exist yet, but we'll add it for the UI
    const response = await documentApi.get<{ documents: Document[] }>('/api/v1/documents');
    return response.data.documents;
  }
};

// LLM Service APIs
export const llmService = {
  askQuestion: async (request: QuestionAnsweringRequest): Promise<QuestionAnsweringResponse> => {
    const response = await llmApi.post<QuestionAnsweringResponse>('/api/v1/qa', request);
    return response.data;
  },

  generateResponse: async (prompt: string, context?: string): Promise<any> => {
    const response = await llmApi.post('/api/v1/generate', {
      prompt,
      context: context || ''
    });
    return response.data;
  },

  testConnection: async (): Promise<any> => {
    const response = await llmApi.get('/api/v1/test');
    return response.data;
  }
};

// Health Check APIs
export const healthService = {
  checkService: async (serviceUrl: string): Promise<HealthStatus> => {
    const client = createApiClient(serviceUrl);
    const response = await client.get<HealthStatus>('/health');
    return response.data;
  },

  checkAllServices: async (): Promise<ServiceStatus[]> => {
    const services: ServiceStatus[] = [
      { name: 'Document Service', port: 8001, status: 'loading', url: SERVICES.DOCUMENT },
      { name: 'Text Processing Service', port: 8002, status: 'loading', url: SERVICES.TEXT_PROCESSING },
      { name: 'Embedding Service', port: 8003, status: 'loading', url: SERVICES.EMBEDDING },
      { name: 'Vector Store Service', port: 8004, status: 'loading', url: SERVICES.VECTOR_STORE },
      { name: 'LLM Service', port: 8005, status: 'loading', url: SERVICES.LLM },
    ];

    const results = await Promise.allSettled(
      services.map(service => healthService.checkService(service.url))
    );

    return services.map((service, index) => ({
      ...service,
      status: results[index].status === 'fulfilled' ? 'healthy' : 'unhealthy'
    }));
  }
};

// Error handling
export const handleApiError = (error: any): string => {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.response?.status) {
      return `Server error: ${error.response.status}`;
    }
    if (error.request) {
      return 'Network error: Unable to connect to server';
    }
  }
  return error.message || 'An unexpected error occurred';
};