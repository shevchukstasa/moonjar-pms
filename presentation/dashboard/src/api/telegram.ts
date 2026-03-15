import apiClient from './client';

export interface BotStatus {
  connected: boolean;
  bot_username?: string;
  bot_name?: string;
  bot_id?: number;
  owner_chat_configured?: boolean;
  message?: string;
  error?: string;
}

export interface TestChatResult {
  success: boolean;
  chat_title?: string;
  chat_type?: string;
  error?: string;
}

export interface TelegramSubscribeResult {
  success: boolean;
  message?: string;
  error?: string;
}

export interface RecentChat {
  chat_id: string;
  title: string;
  type: string;
  username?: string;
}

export interface RecentChatsResult {
  chats: RecentChat[];
  total_updates?: number;
  hint?: string;
  error?: string;
}

export const telegramApi = {
  getBotStatus: (force?: boolean) =>
    apiClient.get<BotStatus>('/telegram/bot-status', {
      params: force ? { force: true } : undefined,
      timeout: 20000,  // 20s max — server retries internally
    }).then((r) => r.data),

  testChat: (chatId: string) =>
    apiClient.post<TestChatResult>('/telegram/test-chat', { chat_id: chatId }).then((r) => r.data),

  getRecentChats: () =>
    apiClient.get<RecentChatsResult>('/telegram/recent-chats').then((r) => r.data),

  subscribe: (telegramUserId: number) =>
    apiClient.post<TelegramSubscribeResult>('/telegram/subscribe', { telegram_user_id: telegramUserId }).then((r) => r.data),

  unsubscribe: () =>
    apiClient.delete<TelegramSubscribeResult>('/telegram/unsubscribe').then((r) => r.data),
};
