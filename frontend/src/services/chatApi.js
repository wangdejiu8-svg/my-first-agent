import { apiRequest, apiStreamRequest } from './apiClient';

export const chatApi = {
  getConversations: () => apiRequest('/conversations/'),

  createConversation: (title) =>
    apiRequest('/conversations/', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),

  updateConversation: (conversationId, payload) =>
    apiRequest(`/conversations/${conversationId}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  deleteConversation: (conversationId) =>
    apiRequest(`/conversations/${conversationId}/`, {
      method: 'DELETE',
    }),

  getMessages: (conversationId) => apiRequest(`/conversations/${conversationId}/messages/`),

  uploadFile: ({ conversationId, file }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }
    return apiRequest('/files/upload/', {
      method: 'POST',
      body: formData,
    });
  },

  sendMessage: ({ conversationId, content, attachmentIds = [] }) =>
    apiRequest('/chat/send/', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        content,
        attachment_ids: attachmentIds,
      }),
    }),

  sendMessageStream: async ({ conversationId, content, attachmentIds = [], onEvent }) => {
    await apiStreamRequest('/chat/send-stream/', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        content,
        attachment_ids: attachmentIds,
      }),
      onLine: (line) => {
        let event;
        try {
          event = JSON.parse(line);
        } catch (error) {
          throw new Error('流式回复解析失败');
        }
        onEvent?.(event);
      },
    });
  },
};
