import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi, type TaskListParams, type TaskItem } from '@/api/tasks';

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
