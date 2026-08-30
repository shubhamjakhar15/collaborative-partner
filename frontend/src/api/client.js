import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // 1. Core Chat Endpoint
  chat: async (userId, projectId, message, metadata = {}) => {
    const payload = {
      project_id: projectId,
      message,
      metadata,
    };
    if (userId) payload.user_id = userId;
    
    const response = await apiClient.post('/chat', payload);
    return response.data;
  },

  // 2. User Preferences (Memory Vault)
  getUserPreferences: async (userId) => {
    const response = await apiClient.get(`/users/${userId}/preferences`);
    return response.data;
  },

  // 3. Project Detail
  getProject: async (userId, projectId, includeMessages = true) => {
    const response = await apiClient.get(`/users/${userId}/projects/${projectId}`, {
      params: { include_messages: includeMessages }
    });
    return response.data;
  },

  // 4. User Projects List
  listUserProjects: async (userId) => {
    const response = await apiClient.get(`/users/${userId}/projects`);
    return response.data;
  }
};
