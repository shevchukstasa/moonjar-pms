import { z } from 'zod';

export const loginSchema = z.object({ email: z.string().email(), password: z.string().min(6) });
export type LoginFormData = z.infer<typeof loginSchema>;

export const orderItemSchema = z.object({
  color: z.string().min(1, 'Color is required'),
  size: z.string().min(1, 'Size is required'),
  application: z.string().optional().default(''),
  finishing: z.string().optional().default(''),
  thickness_mm: z.coerce.number().positive().optional(),
  quantity_pcs: z.coerce.number().int().positive('Quantity must be > 0'),
  product_type: z.string().optional().default('tile'),
});
export type OrderItemFormData = z.infer<typeof orderItemSchema>;

export const orderCreateSchema = z.object({
  order_number: z.string().min(1, 'Order number is required'),
  client: z.string().min(1, 'Client is required'),
  factory_id: z.string().min(1, 'Factory is required'),
  final_deadline: z.string().optional(),
  notes: z.string().optional().default(''),
  mandatory_qc: z.boolean().optional().default(false),
  items: z.array(orderItemSchema).min(1, 'At least one item is required'),
});
export type OrderCreateFormData = z.infer<typeof orderCreateSchema>;
