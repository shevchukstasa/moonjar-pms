import { useQuery, useMutation } from '@tanstack/react-query';
import { telegramApi, type BotStatus, type TestChatResult } from '@/api/telegram';

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
