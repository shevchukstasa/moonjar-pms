import { useQuery } from '@tanstack/react-query';
import { suppliersApi } from '@/api/suppliers';

export interface SupplierItem {
  id: string;
  name: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  material_types: string[] | null;
  default_lead_time_days: number;
  rating: number | null;
  notes: string | null;
  is_active: boolean;
  subgroup_ids: string[];
  subgroup_names: string[];
  created_at: string;
}

export function useSuppliers() {
  return useQuery<{ items: SupplierItem[]; total: number }>({
    queryKey: ['suppliers'],
    queryFn: () => suppliersApi.list(),
  });
}
