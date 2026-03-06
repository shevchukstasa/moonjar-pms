// Auto-generated TypeScript enums from DATABASE_SCHEMA.sql

export const UserRole = {
  OWNER: 'owner',
  ADMINISTRATOR: 'administrator',
  CEO: 'ceo',
  PRODUCTION_MANAGER: 'production_manager',
  QUALITY_MANAGER: 'quality_manager',
  WAREHOUSE: 'warehouse',
  SORTER_PACKER: 'sorter_packer',
  PURCHASER: 'purchaser',
} as const;
export type UserRoleType = (typeof UserRole)[keyof typeof UserRole];

export const OrderSource = {
  SALES_WEBHOOK: 'sales_webhook',
  PDF_UPLOAD: 'pdf_upload',
  MANUAL: 'manual',
} as const;
export type OrderSourceType = (typeof OrderSource)[keyof typeof OrderSource];

export const PositionStatus = {
  PLANNED: 'planned',
  INSUFFICIENT_MATERIALS: 'insufficient_materials',
  AWAITING_RECIPE: 'awaiting_recipe',
  AWAITING_STENCIL_SILKSCREEN: 'awaiting_stencil_silkscreen',
  AWAITING_COLOR_MATCHING: 'awaiting_color_matching',
  ENGOBE_APPLIED: 'engobe_applied',
  ENGOBE_CHECK: 'engobe_check',
  GLAZED: 'glazed',
  PRE_KILN_CHECK: 'pre_kiln_check',
  SENT_TO_GLAZING: 'sent_to_glazing',
  LOADED_IN_KILN: 'loaded_in_kiln',
  FIRED: 'fired',
  TRANSFERRED_TO_SORTING: 'transferred_to_sorting',
  REFIRE: 'refire',
  AWAITING_REGLAZE: 'awaiting_reglaze',
  PACKED: 'packed',
  SENT_TO_QUALITY_CHECK: 'sent_to_quality_check',
  QUALITY_CHECK_DONE: 'quality_check_done',
  READY_FOR_SHIPMENT: 'ready_for_shipment',
  BLOCKED_BY_QM: 'blocked_by_qm',
  CANCELLED: 'cancelled',
} as const;
export type PositionStatusType = (typeof PositionStatus)[keyof typeof PositionStatus];

export const OrderStatus = {
  NEW: 'new',
  IN_PRODUCTION: 'in_production',
  PARTIALLY_READY: 'partially_ready',
  READY_FOR_SHIPMENT: 'ready_for_shipment',
  CANCELLED: 'cancelled',
} as const;
export type OrderStatusType = (typeof OrderStatus)[keyof typeof OrderStatus];

export const ChangeRequestStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const;
export type ChangeRequestStatusType = (typeof ChangeRequestStatus)[keyof typeof ChangeRequestStatus];

export const TaskType = {
  STENCIL_ORDER: 'stencil_order',
  SILK_SCREEN_ORDER: 'silk_screen_order',
  COLOR_MATCHING: 'color_matching',
  MATERIAL_ORDER: 'material_order',
  QUALITY_CHECK: 'quality_check',
  KILN_MAINTENANCE: 'kiln_maintenance',
  SHOWROOM_TRANSFER: 'showroom_transfer',
  PHOTOGRAPHING: 'photographing',
  MANU_CONFIRMATION: 'manu_confirmation',
  PACKING_PHOTO: 'packing_photo',
  RECIPE_CONFIGURATION: 'recipe_configuration',
  REPAIR_SLA_ALERT: 'repair_sla_alert',
  RECONCILIATION_ALERT: 'reconciliation_alert',
} as const;
export type TaskTypeType = (typeof TaskType)[keyof typeof TaskType];

export const TaskStatus = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  DONE: 'done',
  CANCELLED: 'cancelled',
} as const;
export type TaskStatusType = (typeof TaskStatus)[keyof typeof TaskStatus];

export const MaterialType = {
  PIGMENT: 'pigment',
  STONE: 'stone',
  FRIT: 'frit',
  GLAZE: 'glaze',
  STENCIL: 'stencil',
  SILKSCREEN: 'silkscreen',
  OTHER: 'other',
} as const;
export type MaterialTypeType = (typeof MaterialType)[keyof typeof MaterialType];

export const TransactionType = {
  RESERVE: 'reserve',
  CONSUME: 'consume',
  RECEIVE: 'receive',
  ORDER: 'order',
  UNRESERVE: 'unreserve',
  MANUAL_WRITE_OFF: 'manual_write_off',
} as const;
export type TransactionTypeType = (typeof TransactionType)[keyof typeof TransactionType];

export const WriteOffReason = {
  BREAKAGE: 'breakage',
  LOSS: 'loss',
  DAMAGE: 'damage',
  EXPIRED: 'expired',
  ADJUSTMENT: 'adjustment',
  OTHER: 'other',
} as const;
export type WriteOffReasonType = (typeof WriteOffReason)[keyof typeof WriteOffReason];

export const PurchaseStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  SENT: 'sent',
  PARTIALLY_RECEIVED: 'partially_received',
  RECEIVED: 'received',
} as const;
export type PurchaseStatusType = (typeof PurchaseStatus)[keyof typeof PurchaseStatus];

export const ResourceType = {
  KILN: 'kiln',
  GLAZING_STATION: 'glazing_station',
  SORTING_STATION: 'sorting_station',
} as const;
export type ResourceTypeType = (typeof ResourceType)[keyof typeof ResourceType];

export const ResourceStatus = {
  ACTIVE: 'active',
  MAINTENANCE_PLANNED: 'maintenance_planned',
  MAINTENANCE_EMERGENCY: 'maintenance_emergency',
  INACTIVE: 'inactive',
} as const;
export type ResourceStatusType = (typeof ResourceStatus)[keyof typeof ResourceStatus];

export const BatchStatus = {
  SUGGESTED: 'suggested',
  PLANNED: 'planned',
  IN_PROGRESS: 'in_progress',
  DONE: 'done',
} as const;
export type BatchStatusType = (typeof BatchStatus)[keyof typeof BatchStatus];

export const BatchMode = {
  HYBRID: 'hybrid',
  AUTO: 'auto',
} as const;
export type BatchModeType = (typeof BatchMode)[keyof typeof BatchMode];

export const ScheduleSlotStatus = {
  PLANNED: 'planned',
  IN_PROGRESS: 'in_progress',
  DONE: 'done',
  CANCELLED: 'cancelled',
} as const;
export type ScheduleSlotStatusType = (typeof ScheduleSlotStatus)[keyof typeof ScheduleSlotStatus];

export const QcResult = {
  OK: 'ok',
  DEFECT: 'defect',
} as const;
export type QcResultType = (typeof QcResult)[keyof typeof QcResult];

export const QcStage = {
  GLAZING: 'glazing',
  FIRING: 'firing',
  SORTING: 'sorting',
} as const;
export type QcStageType = (typeof QcStage)[keyof typeof QcStage];

export const DefectStage = {
  INCOMING_INSPECTION: 'incoming_inspection',
  PRE_GLAZING: 'pre_glazing',
  AFTER_ENGOBE: 'after_engobe',
  BEFORE_KILN: 'before_kiln',
  AFTER_FIRING: 'after_firing',
  SORTING: 'sorting',
} as const;
export type DefectStageType = (typeof DefectStage)[keyof typeof DefectStage];

export const DefectOutcome = {
  RETURN_TO_WORK: 'return_to_work',
  WRITE_OFF: 'write_off',
  GRINDING: 'grinding',
  REPAIR: 'repair',
  REFIRE: 'refire',
  REGLAZE: 'reglaze',
  TO_STOCK: 'to_stock',
  TO_MANU: 'to_manu',
} as const;
export type DefectOutcomeType = (typeof DefectOutcome)[keyof typeof DefectOutcome];

export const ProductType = {
  TILE: 'tile',
  COUNTERTOP: 'countertop',
  SINK: 'sink',
  _3D: '3d',
} as const;
export type ProductTypeType = (typeof ProductType)[keyof typeof ProductType];

export const ShapeType = {
  RECTANGLE: 'rectangle',
  SQUARE: 'square',
  ROUND: 'round',
  FREEFORM: 'freeform',
  TRIANGLE: 'triangle',
} as const;
export type ShapeTypeType = (typeof ShapeType)[keyof typeof ShapeType];

export const SplitCategory = {
  REPAIR: 'repair',
  COLOR_MISMATCH: 'color_mismatch',
  REGLAZE: 'reglaze',
} as const;
export type SplitCategoryType = (typeof SplitCategory)[keyof typeof SplitCategory];

export const GrindingStatus = {
  IN_STOCK: 'in_stock',
  SENT_TO_MANU: 'sent_to_manu',
  USED_IN_PRODUCTION: 'used_in_production',
} as const;
export type GrindingStatusType = (typeof GrindingStatus)[keyof typeof GrindingStatus];

export const RepairStatus = {
  IN_REPAIR: 'in_repair',
  REPAIRED: 'repaired',
  RETURNED_TO_PRODUCTION: 'returned_to_production',
  WRITTEN_OFF: 'written_off',
} as const;
export type RepairStatusType = (typeof RepairStatus)[keyof typeof RepairStatus];

export const ManuShipmentStatus = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  SHIPPED: 'shipped',
} as const;
export type ManuShipmentStatusType = (typeof ManuShipmentStatus)[keyof typeof ManuShipmentStatus];

export const SurplusDispositionType = {
  SHOWROOM: 'showroom',
  CASTERS: 'casters',
  MANU: 'manu',
} as const;
export type SurplusDispositionTypeType = (typeof SurplusDispositionType)[keyof typeof SurplusDispositionType];

export const MaintenanceStatus = {
  PLANNED: 'planned',
  IN_PROGRESS: 'in_progress',
  DONE: 'done',
} as const;
export type MaintenanceStatusType = (typeof MaintenanceStatus)[keyof typeof MaintenanceStatus];

export const NotificationType = {
  ALERT: 'alert',
  TASK_ASSIGNED: 'task_assigned',
  STATUS_CHANGE: 'status_change',
  MATERIAL_RECEIVED: 'material_received',
  REPAIR_SLA: 'repair_sla',
  RECONCILIATION_DISCREPANCY: 'reconciliation_discrepancy',
  ORDER_CANCELLED: 'order_cancelled',
  KILN_BREAKDOWN: 'kiln_breakdown',
  REFERENCE_CHANGED: 'reference_changed',
  READY_FOR_SHIPMENT: 'ready_for_shipment',
} as const;
export type NotificationTypeType = (typeof NotificationType)[keyof typeof NotificationType];

export const RelatedEntityType = {
  ORDER: 'order',
  POSITION: 'position',
  TASK: 'task',
  MATERIAL: 'material',
  KILN: 'kiln',
} as const;
export type RelatedEntityTypeType = (typeof RelatedEntityType)[keyof typeof RelatedEntityType];

export const TpsDeviationType = {
  POSITIVE: 'positive',
  NEGATIVE: 'negative',
} as const;
export type TpsDeviationTypeType = (typeof TpsDeviationType)[keyof typeof TpsDeviationType];

export const TpsStatus = {
  NORMAL: 'normal',
  WARNING: 'warning',
  CRITICAL: 'critical',
} as const;
export type TpsStatusType = (typeof TpsStatus)[keyof typeof TpsStatus];

export const BufferHealth = {
  GREEN: 'green',
  YELLOW: 'yellow',
  RED: 'red',
} as const;
export type BufferHealthType = (typeof BufferHealth)[keyof typeof BufferHealth];

export const BatchCreator = {
  AUTO: 'auto',
  MANUAL: 'manual',
} as const;
export type BatchCreatorType = (typeof BatchCreator)[keyof typeof BatchCreator];

export const ReferenceAction = {
  CREATE: 'create',
  UPDATE: 'update',
  DELETE: 'delete',
} as const;
export type ReferenceActionType = (typeof ReferenceAction)[keyof typeof ReferenceAction];

export const WebhookAuthMode = {
  BEARER: 'bearer',
  HMAC: 'hmac',
} as const;
export type WebhookAuthModeType = (typeof WebhookAuthMode)[keyof typeof WebhookAuthMode];

export const CastersRemovedReason = {
  USED: 'used',
  SHIPPED_TO_MANU: 'shipped_to_manu',
  OTHER: 'other',
} as const;
export type CastersRemovedReasonType = (typeof CastersRemovedReason)[keyof typeof CastersRemovedReason];

export const MediaType = {
  PHOTO: 'photo',
  VIDEO: 'video',
  AUDIO: 'audio',
  DOCUMENT: 'document',
} as const;
export type MediaTypeType = (typeof MediaType)[keyof typeof MediaType];

export const DashboardType = {
  OWNER: 'owner',
  CEO: 'ceo',
  MANAGER: 'manager',
  QUALITY: 'quality',
  WAREHOUSE: 'warehouse',
  PACKING: 'packing',
  PURCHASER: 'purchaser',
} as const;
export type DashboardTypeType = (typeof DashboardType)[keyof typeof DashboardType];

export const NotificationChannel = {
  IN_APP: 'in_app',
  TELEGRAM: 'telegram',
  BOTH: 'both',
} as const;
export type NotificationChannelType = (typeof NotificationChannel)[keyof typeof NotificationChannel];

export const ExpenseType = {
  OPEX: 'opex',
  CAPEX: 'capex',
} as const;
export type ExpenseTypeType = (typeof ExpenseType)[keyof typeof ExpenseType];

export const ExpenseCategory = {
  MATERIALS: 'materials',
  LABOR: 'labor',
  UTILITIES: 'utilities',
  MAINTENANCE: 'maintenance',
  EQUIPMENT: 'equipment',
  LOGISTICS: 'logistics',
  OTHER: 'other',
} as const;
export type ExpenseCategoryType = (typeof ExpenseCategory)[keyof typeof ExpenseCategory];

export const ReconciliationStatus = {
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
} as const;
export type ReconciliationStatusType = (typeof ReconciliationStatus)[keyof typeof ReconciliationStatus];

export const ProblemCardMode = {
  SIMPLE: 'simple',
  FULL_8D: 'full_8d',
} as const;
export type ProblemCardModeType = (typeof ProblemCardMode)[keyof typeof ProblemCardMode];

export const ProblemCardStatus = {
  OPEN: 'open',
  IN_PROGRESS: 'in_progress',
  CLOSED: 'closed',
} as const;
export type ProblemCardStatusType = (typeof ProblemCardStatus)[keyof typeof ProblemCardStatus];

export const QmBlockType = {
  POSITION: 'position',
  BATCH: 'batch',
} as const;
export type QmBlockTypeType = (typeof QmBlockType)[keyof typeof QmBlockType];

export const KilnConstantsMode = {
  MANUAL: 'manual',
  PRODUCTION: 'production',
} as const;
export type KilnConstantsModeType = (typeof KilnConstantsMode)[keyof typeof KilnConstantsMode];

export const LanguagePreference = {
  EN: 'en',
  RU: 'ru',
  ID: 'id',
} as const;
export type LanguagePreferenceType = (typeof LanguagePreference)[keyof typeof LanguagePreference];

export const AuditActionType = {
  LOGIN_SUCCESS: 'login_success',
  LOGIN_FAILED: 'login_failed',
  LOGOUT: 'logout',
  TOKEN_REFRESH: 'token_refresh',
  PASSWORD_CHANGE: 'password_change',
  ROLE_CHANGE: 'role_change',
  USER_CREATE: 'user_create',
  USER_DEACTIVATE: 'user_deactivate',
  PERMISSION_GRANT: 'permission_grant',
  PERMISSION_REVOKE: 'permission_revoke',
  DATA_EXPORT: 'data_export',
  FILE_UPLOAD: 'file_upload',
  FILE_DOWNLOAD: 'file_download',
  SETTINGS_CHANGE: 'settings_change',
  WEBHOOK_RECEIVED: 'webhook_received',
  TOTP_SETUP: 'totp_setup',
  TOTP_DISABLE: 'totp_disable',
  SESSION_REVOKE: 'session_revoke',
  IP_ALLOWLIST_CHANGE: 'ip_allowlist_change',
  FACTORY_CREATE: 'factory_create',
  FACTORY_DELETE: 'factory_delete',
  ANOMALY_DETECTED: 'anomaly_detected',
} as const;
export type AuditActionTypeType = (typeof AuditActionType)[keyof typeof AuditActionType];

export const IpScope = {
  ADMIN_PANEL: 'admin_panel',
  WEBHOOK: 'webhook',
  ALL: 'all',
} as const;
export type IpScopeType = (typeof IpScope)[keyof typeof IpScope];
