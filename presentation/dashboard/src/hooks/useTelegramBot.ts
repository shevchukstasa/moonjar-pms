import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { telegramApi, type BotStatus, type TestChatResult, type TelegramSubscribeResult, type RecentChatsResult } from '@/api/telegram';

export function useBotStatus() {
  return useQuery<BotStatus>({
    queryKey: ['telegram', 'bot-status'],
    queryFn: () => telegramApi.getBotStatus(),
    staleTime: 5 * 60 * 1000,  // 5 min — server caches too
    retry: 0,  // don't retry on timeout — server already retries
  });
}

export function useRefreshBotStatus() {
  const qc = useQueryClient();
  return useMutation<BotStatus, Error, void>({
    mutationFn: () => telegramApi.getBotStatus(true),
    onSuccess: (data) => {
      qc.setQueryData(['telegram', 'bot-status'], data);
    },
  });
}

export function useTestChat() {
  return useMutation<TestChatResult, Error, string>({
    mutationFn: (chatId: string) => telegramApi.testChat(chatId),
  });
}

export function useRecentChats() {
  return useMutation<RecentChatsResult, Error, void>({
    mutationFn: () => telegramApi.getRecentChats(),
  });
}

export function useTelegramSubscribe() {
  const qc = useQueryClient();
  return useMutation<TelegramSubscribeResult, Error, number>({
    mutationFn: (telegramUserId: number) => telegramApi.subscribe(telegramUserId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['telegram'] });
    },
  });
}

export function useTelegramUnsubscribe() {
  const qc = useQueryClient();
  return useMutation<TelegramSubscribeResult, Error, void>({
    mutationFn: () => telegramApi.unsubscribe(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['telegram'] });
    },
  });
}
