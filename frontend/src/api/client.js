import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // 1. Core Chat Endpoint with Attachments
  chat: async (userId, projectId, message, metadata = {}, attachments = []) => {
    const payload = {
      project_id: projectId,
      message,
      metadata,
      attachments,
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

  // 3. Project Detail (Roadmap, Messages, Files)
  getProject: async (userId, projectId, includeMessages = true, includeFiles = true) => {
    const response = await apiClient.get(`/users/${userId}/projects/${projectId}`, {
      params: {
        include_messages: includeMessages,
        include_files: includeFiles,
      }
    });
    return response.data;
  },

  // 4. User Projects List
  listUserProjects: async (userId) => {
    const response = await apiClient.get(`/users/${userId}/projects`);
    return response.data;
  },

  // 5. Project Files List
  getProjectFiles: async (userId, projectId) => {
    const response = await apiClient.get(`/users/${userId}/projects/${projectId}/files`);
    return response.data;
  },

  // 6. Upload Project File
  uploadFile: async (userId, projectId, filePayload) => {
    const response = await apiClient.post(`/users/${userId}/projects/${projectId}/files`, filePayload);
    return response.data;
  },

  // 7. Delete Project File
  deleteFile: async (userId, projectId, fileId) => {
    const response = await apiClient.delete(`/users/${userId}/projects/${projectId}/files/${fileId}`);
    return response.data;
  },
};
