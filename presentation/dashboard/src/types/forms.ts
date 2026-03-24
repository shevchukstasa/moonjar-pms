import { z } from 'zod';

export const loginSchema = z.object({ email: z.string().email(), password: z.string().min(6) });
export type LoginFormData = z.infer<typeof loginSchema>;

export const SHAPE_OPTIONS = [
  { value: 'rectangle', label: 'Rectangle' },
  { value: 'square', label: 'Square' },
  { value: 'round', label: 'Round' },
  { value: 'triangle', label: 'Triangle' },
  { value: 'octagon', label: 'Octagon' },
  { value: 'freeform', label: 'Freeform' },
] as const;

export const BOWL_SHAPE_OPTIONS = [
  { value: '', label: 'N/A' },
  { value: 'parallelepiped', label: 'Parallelepiped' },
  { value: 'half_oval', label: 'Half Oval' },
  { value: 'other', label: 'Other' },
] as const;

export const orderItemSchema = z.object({
  color: z.string().min(1, 'Color is required'),
  size: z.string().min(1, 'Size is required'),
  application: z.string().optional().default(''),
  finishing: z.string().optional().default(''),
  collection: z.string().optional().default(''),
  thickness_mm: z.coerce.number().positive().optional().nullable(),
  place_of_application: z.string().optional().default('face'),
  quantity_pcs: z.coerce.number().positive('Quantity must be > 0'),
  quantity_unit: z.string().optional().default('pcs'),
  product_type: z.string().optional().default('tile'),
  // Shape & dimensions for glaze surface area
  shape: z.string().optional().default('rectangle'),
  length_cm: z.coerce.number().positive().optional().nullable(),
  width_cm: z.coerce.number().positive().optional().nullable(),
  depth_cm: z.coerce.number().positive().optional().nullable(),
  bowl_shape: z.string().optional().default(''),
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

// --- User Management ---
export const ROLE_OPTIONS = [
  { value: 'owner', label: 'Owner' },
  { value: 'administrator', label: 'Administrator' },
  { value: 'ceo', label: 'CEO' },
  { value: 'production_manager', label: 'Production Manager' },
  { value: 'quality_manager', label: 'Quality Manager' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'sorter_packer', label: 'Sorter / Packer' },
  { value: 'purchaser', label: 'Purchaser' },
] as const;

export const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Russian' },
  { value: 'id', label: 'Indonesian' },
] as const;

export const userCreateSchema = z.object({
  email: z.string().email('Invalid email'),
  name: z.string().min(1, 'Name is required'),
  role: z.string().min(1, 'Role is required'),
  password: z.string().optional().default(''),
  google_auth: z.boolean().optional().default(false),
  factory_ids: z.array(z.string()).optional().default([]),
  language: z.string().optional().default('en'),
}).refine(
  (data) => data.google_auth || (data.password && data.password.length >= 6),
  { message: 'Password (min 6 chars) required unless Google Auth is enabled', path: ['password'] },
);
export type UserCreateFormData = z.infer<typeof userCreateSchema>;

export const userUpdateSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  role: z.string().min(1, 'Role is required'),
  language: z.string().optional().default('en'),
  factory_ids: z.array(z.string()).optional().default([]),
});
export type UserUpdateFormData = z.infer<typeof userUpdateSchema>;

export const TELEGRAM_LANGUAGE_OPTIONS = [
  { value: 'id', label: 'Indonesian' },
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Russian' },
] as const;

export const factoryCreateSchema = z.object({
  name: z.string().min(1, 'Factory name is required'),
  location: z.string().optional().default(''),
  timezone: z.string().optional().default('Asia/Makassar'),
  is_active: z.boolean().optional().default(true),
  // Telegram
  masters_group_chat_id: z.string()
    .refine(v => !v || /^-?\d+$/.test(v), 'Must be a valid number')
    .optional().default(''),
  purchaser_chat_id: z.string()
    .refine(v => !v || /^-?\d+$/.test(v), 'Must be a valid number')
    .optional().default(''),
  telegram_language: z.string().optional().default('id'),
});
export type FactoryFormData = z.infer<typeof factoryCreateSchema>;

// --- Kiln Management ---
export const KILN_TYPE_OPTIONS = [
  { value: 'big', label: 'Large Kiln' },
  { value: 'small', label: 'Small Kiln' },
  { value: 'raku', label: 'Raku Kiln' },
] as const;

export const KILN_STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'maintenance_planned', label: 'Maintenance Planned' },
  { value: 'maintenance_emergency', label: 'Emergency Maintenance' },
  { value: 'inactive', label: 'Inactive' },
] as const;

// height is optional — working area of single-level kilns has no height
const dimensionSchema = z.object({
  width: z.coerce.number().positive('Width required'),
  depth: z.coerce.number().positive('Depth required'),
  height: z.coerce.number().min(0).optional().nullable(),
});

export const kilnCreateSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  kiln_type: z.string().min(1, 'Kiln type is required'),
  kiln_dimensions_cm: dimensionSchema,
  kiln_working_area_cm: dimensionSchema,
  kiln_multi_level: z.boolean().default(false),
  // coefficient can be > 1 for some kilns (e.g. raku with attrition)
  kiln_coefficient: z.coerce.number().min(0).max(2).default(0.8),
  thermocouple: z.string().optional().default(''),
  control_cable: z.string().optional().default(''),
  control_device: z.string().optional().default(''),
});
export type KilnCreateFormData = z.infer<typeof kilnCreateSchema>;

export const kilnEditSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  factory_id: z.string().min(1, 'Factory is required'),
  kiln_dimensions_cm: dimensionSchema,
  kiln_working_area_cm: dimensionSchema,
  kiln_multi_level: z.boolean().default(false),
  kiln_coefficient: z.coerce.number().min(0).max(2).default(0.8),
  thermocouple: z.string().optional().default(''),
  control_cable: z.string().optional().default(''),
  control_device: z.string().optional().default(''),
});
export type KilnEditFormData = z.infer<typeof kilnEditSchema>;
