import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { telegramApi, type BotStatus, type TestChatResult, type TelegramSubscribeResult } from '@/api/telegram';

export function useBotStatus() {
  return useQuery<BotStatus>({
    queryKey: ['telegram', 'bot-status'],
    queryFn: () => telegramApi.getBotStatus(),
    staleTime: 60 * 1000, // 1 min cache
    retry: 1,
  });
}

export function useTestChat() {
  return useMutation<TestChatResult, Error, string>({
    mutationFn: (chatId: string) => telegramApi.testChat(chatId),
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
