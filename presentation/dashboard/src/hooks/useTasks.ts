import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi, type TaskListParams, type TaskItem, type ShortageResolutionInput } from '@/api/tasks';

export function useTasks(params?: TaskListParams) {
  return useQuery<{ items: TaskItem[]; total: number }>({
    queryKey: ['tasks', params],
    queryFn: () => tasksApi.list(params),
  });
}

export function useSorterTasks(factoryId?: string) {
  const params: TaskListParams = {
    assigned_role: 'sorter_packer',
    status: 'pending,in_progress',
    ...(factoryId ? { factory_id: factoryId } : {}),
  };
  return useQuery<{ items: TaskItem[]; total: number }>({
    queryKey: ['tasks', 'sorter', params],
    queryFn: () => tasksApi.list(params),
  });
}

export function useCompleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tasksApi.complete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

export function useTask(id?: string) {
  return useQuery<TaskItem>({
    queryKey: ['tasks', id],
    queryFn: () => tasksApi.get(id!),
    enabled: !!id,
  });
}

export function useShortageResolution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ShortageResolutionInput }) =>
      tasksApi.resolveShortage(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['positions'] });
      qc.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useShortageTasksForManager(factoryId?: string) {
  const params: TaskListParams = {
    task_type: 'stock_shortage',
    status: 'pending',
    ...(factoryId ? { factory_id: factoryId } : {}),
  };
  return useQuery<{ items: TaskItem[]; total: number }>({
    queryKey: ['tasks', 'shortage', params],
    queryFn: () => tasksApi.list(params),
  });
}
