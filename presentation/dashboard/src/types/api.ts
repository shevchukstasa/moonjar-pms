export interface LoginRequest { email: string; password: string; }
export interface LoginResponse { access_token: string; token_type: string; user: { id: string; email: string; role: string; name: string }; }
export interface ApiError { detail: string; code?: string; field?: string; }
export interface ListParams { page?: number; per_page?: number; factory_id?: string; sort_by?: string; sort_order?: 'asc' | 'desc'; search?: string; }
