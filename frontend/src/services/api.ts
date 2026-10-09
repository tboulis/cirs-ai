import axios, { AxiosResponse } from 'axios';
import {
  ChatRequest,
  ChatResponse,
  Conversation,
  Message,
  Document,
  DocumentUpload,
  DocumentSearchRequest,
  DocumentSearchResult,
  ModelInfo,
  HealthResponse,
  PaginationParams,
} from '../types';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization header if token exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any)['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw error;
  }
);

// Chat API functions
export const chatApi = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response: AxiosResponse<ChatResponse> = await api.post('/chat', request);
    return response.data;
  },

  getConversations: async (params?: PaginationParams): Promise<Conversation[]> => {
    const response: AxiosResponse<Conversation[]> = await api.get('/conversations', { params });
    return response.data;
  },

  getConversationMessages: async (
    conversationId: number,
    params?: PaginationParams
  ): Promise<Message[]> => {
    const response: AxiosResponse<Message[]> = await api.get(
      `/conversations/${conversationId}/messages`,
      { params }
    );
    return response.data;
  },

  deleteConversation: async (conversationId: number): Promise<void> => {
    await api.delete(`/conversations/${conversationId}`);
  },

  createSession: async (): Promise<any> => {
    const response: AxiosResponse<any> = await api.post('/sessions');
    return response.data;
  },
};

// Document API functions
export const documentApi = {
  uploadDocument: async (file: File, metadata: DocumentUpload): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata.title) formData.append('title', metadata.title);
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.keywords) formData.append('keywords', metadata.keywords);

    const response: AxiosResponse<Document> = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getDocuments: async (params?: { skip?: number; limit?: number; processed_only?: boolean }): Promise<Document[]> => {
    const response: AxiosResponse<Document[]> = await api.get('/documents', { params });
    return response.data;
  },

  // The list endpoint is paginated (at most 100 per request); fetch every page.
  getAllDocuments: async (params?: { processed_only?: boolean }): Promise<Document[]> => {
    const pageSize = 100;
    const all: Document[] = [];
    for (let skip = 0; ; skip += pageSize) {
      const page = await documentApi.getDocuments({ ...params, skip, limit: pageSize });
      all.push(...page);
      if (page.length < pageSize) return all;
    }
  },

  getDocument: async (documentId: number): Promise<Document> => {
    const response: AxiosResponse<Document> = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  processDocument: async (
    documentId: number,
    options: { chunk_size?: number; chunk_overlap?: number } = {}
  ): Promise<any> => {
    const response: AxiosResponse<any> = await api.post(`/documents/${documentId}/process`, {
      document_id: documentId,
      ...options,
    });
    return response.data;
  },

  searchDocuments: async (request: DocumentSearchRequest): Promise<DocumentSearchResult[]> => {
    const response: AxiosResponse<DocumentSearchResult[]> = await api.post('/documents/search', request);
    return response.data;
  },

  deleteDocument: async (documentId: number): Promise<void> => {
    await api.delete(`/documents/${documentId}`);
  },
};

// Health and system API functions
export const systemApi = {
  getHealth: async (): Promise<HealthResponse> => {
    const response: AxiosResponse<HealthResponse> = await api.get('/health');
    return response.data;
  },

  getModels: async (): Promise<{ models: ModelInfo[]; default_model: string }> => {
    const response: AxiosResponse<{ models: ModelInfo[]; default_model: string }> = await api.get('/models');
    return response.data;
  },
};

// Root API check
export const getRootInfo = async (): Promise<any> => {
  const response: AxiosResponse<any> = await axios.get('/');
  return response.data;
};

export default api; 

// ---------------- Auth API ----------------
export const authApi = {
  login: async (username: string, password: string): Promise<string> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const resp = await api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    const token = (resp.data?.access_token as string) || '';
    if (!token) throw new Error('No token returned');
    localStorage.setItem('token', token);
    // notify app of auth state change
    window.dispatchEvent(new Event('auth-changed'));
    return token;
  },
  logout: (): void => {
    localStorage.removeItem('token');
    window.dispatchEvent(new Event('auth-changed'));
  },
  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('token');
  },
};