import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  materialGroupsApi,
  type MaterialGroup,
  type MaterialSubgroup,
  type MaterialGroupInput,
  type MaterialGroupUpdate,
  type MaterialSubgroupInput,
  type MaterialSubgroupUpdate,
} from '@/api/materialGroups';

export type { MaterialGroup, MaterialSubgroup };

// ── Hierarchy ────────────────────────────────────────────────────────────

export function useMaterialHierarchy(includeInactive = false) {
  return useQuery<MaterialGroup[]>({
    queryKey: ['material-groups', 'hierarchy', includeInactive],
    queryFn: () => materialGroupsApi.getHierarchy(includeInactive),
    staleTime: 5 * 60_000, // 5 min — hierarchy rarely changes
  });
}

// ── Groups ───────────────────────────────────────────────────────────────

export function useMaterialGroups(includeInactive = false) {
  return useQuery({
    queryKey: ['material-groups', 'groups', includeInactive],
    queryFn: () => materialGroupsApi.listGroups(includeInactive),
    staleTime: 5 * 60_000,
  });
}

export function useCreateMaterialGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MaterialGroupInput) => materialGroupsApi.createGroup(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['material-groups'] });
    },
  });
}

export function useUpdateMaterialGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MaterialGroupUpdate }) =>
      materialGroupsApi.updateGroup(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['material-groups'] });
    },
  });
}

// ── Subgroups ────────────────────────────────────────────────────────────

export function useMaterialSubgroups(groupId?: string, includeInactive = false) {
  return useQuery<MaterialSubgroup[]>({
    queryKey: ['material-groups', 'subgroups', groupId, includeInactive],
    queryFn: () =>
      materialGroupsApi.listSubgroups({
        group_id: groupId,
        include_inactive: includeInactive || undefined,
      }),
    staleTime: 5 * 60_000,
  });
}

export function useCreateMaterialSubgroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MaterialSubgroupInput) => materialGroupsApi.createSubgroup(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['material-groups'] });
    },
  });
}

export function useUpdateMaterialSubgroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MaterialSubgroupUpdate }) =>
      materialGroupsApi.updateSubgroup(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['material-groups'] });
    },
  });
}
