import apiClient from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export const aiChatApi = {
  chat: (data: { message: string; session_id?: string }) =>
    apiClient.post('/ai-chat/chat', data).then((r) => r.data),
  listSessions: () =>
    apiClient.get<{ items: ChatSession[] }>('/ai-chat/sessions').then((r) => r.data),
  getMessages: (sessionId: string) =>
    apiClient.get<{ items: ChatMessage[] }>(`/ai-chat/sessions/${sessionId}/messages`).then((r) => r.data),
};
