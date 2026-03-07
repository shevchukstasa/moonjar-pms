import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi, type UserListParams } from '@/api/users';

export interface UserItem {
  id: string;
  email: string;
  name: string;
  role: string;
  language: string | null;
  is_active: boolean;
  totp_enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
  factories: { id: string; name: string }[];
}

export function useUsers(params?: UserListParams) {
  return useQuery<{ items: UserItem[]; total: number; page: number; per_page: number }>({
    queryKey: ['users', params],
    queryFn: () => usersApi.list(params),
  });
}

export function useUser(id: string | null) {
  return useQuery<UserItem>({
    queryKey: ['users', id],
    queryFn: () => usersApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; name: string; role: string; password: string; factory_ids?: string[]; language?: string }) =>
      usersApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); },
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; role?: string; language?: string; factory_ids?: string[] } }) =>
      usersApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); },
  });
}

export function useToggleUserActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.toggleActive(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); },
  });
}
