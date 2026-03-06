export interface User { id: string; email: string; name: string; role: string; is_active: boolean; created_at: string; }
export interface Factory { id: string; name: string; location: string; is_active: boolean; }
export interface Order { id: string; order_number: string; client: string; factory_id: string; status: string; priority: string; deadline: string | null; created_at: string; }
export interface OrderPosition { id: string; order_id: string; position_number: number; product_type: string; color: string; quantity_pcs: number; area_sqm: number; status: string; }
export interface Material { id: string; name: string; factory_id: string; balance: number; min_balance: number; unit: string; material_type: string; is_low_stock: boolean; }
export interface Notification { id: string; title: string; body: string | null; type: string; is_read: boolean; created_at: string; }
export interface PaginatedResponse<T> { items: T[]; total: number; page: number; per_page: number; }
