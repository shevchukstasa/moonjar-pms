"""
Moonjar PMS — Enum definitions (auto-generated from DATABASE_SCHEMA.sql)
"""

from enum import Enum

class UserRole(str, Enum):
    OWNER = 'owner'
    ADMINISTRATOR = 'administrator'
    CEO = 'ceo'
    PRODUCTION_MANAGER = 'production_manager'
    QUALITY_MANAGER = 'quality_manager'
    WAREHOUSE = 'warehouse'
    SORTER_PACKER = 'sorter_packer'
    PURCHASER = 'purchaser'
    MASTER = 'master'
    SENIOR_MASTER = 'senior_master'

class OrderSource(str, Enum):
    SALES_WEBHOOK = 'sales_webhook'
    PDF_UPLOAD = 'pdf_upload'
    MANUAL = 'manual'

class PositionStatus(str, Enum):
    PLANNED = 'planned'
    INSUFFICIENT_MATERIALS = 'insufficient_materials'
    AWAITING_RECIPE = 'awaiting_recipe'
    AWAITING_STENCIL_SILKSCREEN = 'awaiting_stencil_silkscreen'
    AWAITING_COLOR_MATCHING = 'awaiting_color_matching'
    AWAITING_SIZE_CONFIRMATION = 'awaiting_size_confirmation'
    ENGOBE_APPLIED = 'engobe_applied'
    ENGOBE_CHECK = 'engobe_check'
    GLAZED = 'glazed'
    PRE_KILN_CHECK = 'pre_kiln_check'
    SENT_TO_GLAZING = 'sent_to_glazing'
    LOADED_IN_KILN = 'loaded_in_kiln'
    FIRED = 'fired'
    TRANSFERRED_TO_SORTING = 'transferred_to_sorting'
    REFIRE = 'refire'
    AWAITING_REGLAZE = 'awaiting_reglaze'
    PACKED = 'packed'
    SENT_TO_QUALITY_CHECK = 'sent_to_quality_check'
    QUALITY_CHECK_DONE = 'quality_check_done'
    READY_FOR_SHIPMENT = 'ready_for_shipment'
    BLOCKED_BY_QM = 'blocked_by_qm'
    SHIPPED = 'shipped'
    CANCELLED = 'cancelled'

class OrderStatus(str, Enum):
    NEW = 'new'
    IN_PRODUCTION = 'in_production'
    PARTIALLY_READY = 'partially_ready'
    READY_FOR_SHIPMENT = 'ready_for_shipment'
    SHIPPED = 'shipped'
    CANCELLED = 'cancelled'

class ChangeRequestStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class TaskType(str, Enum):
    STENCIL_ORDER = 'stencil_order'
    SILK_SCREEN_ORDER = 'silk_screen_order'
    COLOR_MATCHING = 'color_matching'
    MATERIAL_ORDER = 'material_order'
    QUALITY_CHECK = 'quality_check'
    KILN_MAINTENANCE = 'kiln_maintenance'
    SHOWROOM_TRANSFER = 'showroom_transfer'
    PHOTOGRAPHING = 'photographing'
    MANA_CONFIRMATION = 'mana_confirmation'
    PACKING_PHOTO = 'packing_photo'
    RECIPE_CONFIGURATION = 'recipe_configuration'
    REPAIR_SLA_ALERT = 'repair_sla_alert'
    RECONCILIATION_ALERT = 'reconciliation_alert'
    STOCK_SHORTAGE = 'stock_shortage'
    STOCK_TRANSFER = 'stock_transfer'
    SIZE_RESOLUTION = 'size_resolution'

class TaskStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'
    CANCELLED = 'cancelled'

class MaterialType(str, Enum):
    STONE = 'stone'               # Камень
    PIGMENT = 'pigment'           # Пигменты
    FRIT = 'frit'                 # Фритты
    OXIDE_CARBONATE = 'oxide_carbonate'  # Оксиды и карбонаты
    OTHER_BULK = 'other_bulk'     # Прочее сыпучее
    PACKAGING = 'packaging'       # Упаковка
    CONSUMABLE = 'consumable'     # Расходные материалы
    OTHER = 'other'               # Прочее

class TransactionType(str, Enum):
    RESERVE = 'reserve'
    CONSUME = 'consume'
    RECEIVE = 'receive'
    ORDER = 'order'
    UNRESERVE = 'unreserve'
    MANUAL_WRITE_OFF = 'manual_write_off'
    INVENTORY = 'inventory'

class WriteOffReason(str, Enum):
    BREAKAGE = 'breakage'
    LOSS = 'loss'
    DAMAGE = 'damage'
    EXPIRED = 'expired'
    ADJUSTMENT = 'adjustment'
    OTHER = 'other'

class PurchaseStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    SENT = 'sent'
    PARTIALLY_RECEIVED = 'partially_received'
    RECEIVED = 'received'

class ResourceType(str, Enum):
    KILN = 'kiln'
    GLAZING_STATION = 'glazing_station'
    SORTING_STATION = 'sorting_station'

class ResourceStatus(str, Enum):
    ACTIVE = 'active'
    MAINTENANCE_PLANNED = 'maintenance_planned'
    MAINTENANCE_EMERGENCY = 'maintenance_emergency'
    INACTIVE = 'inactive'

class BatchStatus(str, Enum):
    SUGGESTED = 'suggested'
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'

class BatchMode(str, Enum):
    HYBRID = 'hybrid'
    AUTO = 'auto'

class ScheduleSlotStatus(str, Enum):
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'
    CANCELLED = 'cancelled'

class QcResult(str, Enum):
    OK = 'ok'
    DEFECT = 'defect'

class QcStage(str, Enum):
    GLAZING = 'glazing'
    FIRING = 'firing'
    SORTING = 'sorting'

class DefectStage(str, Enum):
    INCOMING_INSPECTION = 'incoming_inspection'
    PRE_GLAZING = 'pre_glazing'
    AFTER_ENGOBE = 'after_engobe'
    BEFORE_KILN = 'before_kiln'
    AFTER_FIRING = 'after_firing'
    SORTING = 'sorting'

class DefectOutcome(str, Enum):
    RETURN_TO_WORK = 'return_to_work'
    WRITE_OFF = 'write_off'
    GRINDING = 'grinding'
    REPAIR = 'repair'
    REFIRE = 'refire'
    REGLAZE = 'reglaze'
    TO_STOCK = 'to_stock'
    TO_MANA = 'to_mana'

class ProductType(str, Enum):
    TILE = 'tile'
    COUNTERTOP = 'countertop'
    SINK = 'sink'
    _3D = '3d'

class ShapeType(str, Enum):
    RECTANGLE = 'rectangle'
    SQUARE = 'square'
    ROUND = 'round'
    FREEFORM = 'freeform'
    TRIANGLE = 'triangle'
    OCTAGON = 'octagon'

class BowlShape(str, Enum):
    PARALLELEPIPED = 'parallelepiped'   # Rectangular bowl
    HALF_OVAL = 'half_oval'             # Half-oval (ellipsoidal) bowl
    OTHER = 'other'                     # Arbitrary bowl shape

class SplitCategory(str, Enum):
    REPAIR = 'repair'                   # Needs re-glazing → SENT_TO_GLAZING
    REFIRE = 'refire'                   # Already glazed, just needs re-firing → REFIRE status
    COLOR_MISMATCH = 'color_mismatch'   # Wrong color, re-starts from PLANNED
    REGLAZE = 'reglaze'                 # Legacy / explicit re-glaze path

class GrindingStatus(str, Enum):
    IN_STOCK = 'in_stock'
    SENT_TO_MANA = 'sent_to_mana'
    USED_IN_PRODUCTION = 'used_in_production'

class RepairStatus(str, Enum):
    IN_REPAIR = 'in_repair'
    REPAIRED = 'repaired'
    RETURNED_TO_PRODUCTION = 'returned_to_production'
    WRITTEN_OFF = 'written_off'

class ManaShipmentStatus(str, Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    SHIPPED = 'shipped'

class SurplusDispositionType(str, Enum):
    SHOWROOM = 'showroom'
    CASTERS = 'casters'
    MANA = 'mana'

class MaintenanceStatus(str, Enum):
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'

class NotificationType(str, Enum):
    ALERT = 'alert'
    TASK_ASSIGNED = 'task_assigned'
    STATUS_CHANGE = 'status_change'
    MATERIAL_RECEIVED = 'material_received'
    REPAIR_SLA = 'repair_sla'
    RECONCILIATION_DISCREPANCY = 'reconciliation_discrepancy'
    ORDER_CANCELLED = 'order_cancelled'
    KILN_BREAKDOWN = 'kiln_breakdown'
    REFERENCE_CHANGED = 'reference_changed'
    READY_FOR_SHIPMENT = 'ready_for_shipment'
    STOCK_SHORTAGE = 'stock_shortage'
    CANCELLATION_REQUEST = 'cancellation_request'

class RelatedEntityType(str, Enum):
    ORDER = 'order'
    POSITION = 'position'
    TASK = 'task'
    MATERIAL = 'material'
    KILN = 'kiln'

class TpsDeviationType(str, Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'

class TpsStatus(str, Enum):
    NORMAL = 'normal'
    WARNING = 'warning'
    CRITICAL = 'critical'

class BufferHealth(str, Enum):
    GREEN = 'green'
    YELLOW = 'yellow'
    RED = 'red'

class BatchCreator(str, Enum):
    AUTO = 'auto'
    MANUAL = 'manual'

class ReferenceAction(str, Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'

class WebhookAuthMode(str, Enum):
    BEARER = 'bearer'
    HMAC = 'hmac'

class CastersRemovedReason(str, Enum):
    USED = 'used'
    SHIPPED_TO_MANA = 'shipped_to_mana'
    OTHER = 'other'

class MediaType(str, Enum):
    PHOTO = 'photo'
    VIDEO = 'video'
    AUDIO = 'audio'
    DOCUMENT = 'document'

class DashboardType(str, Enum):
    OWNER = 'owner'
    CEO = 'ceo'
    MANAGER = 'manager'
    QUALITY = 'quality'
    WAREHOUSE = 'warehouse'
    PACKING = 'packing'
    PURCHASER = 'purchaser'

class NotificationChannel(str, Enum):
    IN_APP = 'in_app'
    TELEGRAM = 'telegram'
    BOTH = 'both'

class ExpenseType(str, Enum):
    OPEX = 'opex'
    CAPEX = 'capex'

class ExpenseCategory(str, Enum):
    MATERIALS = 'materials'
    LABOR = 'labor'
    UTILITIES = 'utilities'
    MAINTENANCE = 'maintenance'
    EQUIPMENT = 'equipment'
    LOGISTICS = 'logistics'
    OTHER = 'other'

class ReconciliationStatus(str, Enum):
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class ReceivingApprovalMode(str, Enum):
    ALL = 'all'          # PM approves every delivery
    AUTO = 'auto'        # Auto-approve if no quality issues

class ProblemCardMode(str, Enum):
    SIMPLE = 'simple'
    FULL_8D = 'full_8d'

class ProblemCardStatus(str, Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    CLOSED = 'closed'

class QmBlockType(str, Enum):
    POSITION = 'position'
    BATCH = 'batch'

class KilnConstantsMode(str, Enum):
    MANUAL = 'manual'
    PRODUCTION = 'production'

class LanguagePreference(str, Enum):
    EN = 'en'
    RU = 'ru'
    ID = 'id'

class AuditActionType(str, Enum):
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILED = 'login_failed'
    LOGOUT = 'logout'
    TOKEN_REFRESH = 'token_refresh'
    PASSWORD_CHANGE = 'password_change'
    ROLE_CHANGE = 'role_change'
    USER_CREATE = 'user_create'
    USER_DEACTIVATE = 'user_deactivate'
    PERMISSION_GRANT = 'permission_grant'
    PERMISSION_REVOKE = 'permission_revoke'
    DATA_EXPORT = 'data_export'
    FILE_UPLOAD = 'file_upload'
    FILE_DOWNLOAD = 'file_download'
    SETTINGS_CHANGE = 'settings_change'
    WEBHOOK_RECEIVED = 'webhook_received'
    TOTP_SETUP = 'totp_setup'
    TOTP_DISABLE = 'totp_disable'
    SESSION_REVOKE = 'session_revoke'
    IP_ALLOWLIST_CHANGE = 'ip_allowlist_change'
    FACTORY_CREATE = 'factory_create'
    FACTORY_DELETE = 'factory_delete'
    ANOMALY_DETECTED = 'anomaly_detected'

class IpScope(str, Enum):
    ADMIN_PANEL = 'admin_panel'
    WEBHOOK = 'webhook'
    ALL = 'all'

class BackupStatus(str, Enum):
    IN_PROGRESS = 'in_progress'
    SUCCESS = 'success'
    FAILED = 'failed'

class BackupType(str, Enum):
    SCHEDULED = 'scheduled'
    MANUAL = 'manual'


class EngobeType(str, Enum):
    STANDARD = 'standard'
    SHELF_COATING = 'shelf_coating'
    HOLE_FILLER = 'hole_filler'


class NightAlertLevel(str, Enum):
    MORNING = 'morning'
    REPEAT = 'repeat'
    CALL = 'call'


# --- Stock Collection Detection ---

STOCK_COLLECTION_NAMES = {"сток", "stock"}


def is_stock_collection(collection: str | None) -> bool:
    """Check if collection name indicates pre-made stock (skip manufacturing)."""
    if not collection:
        return False
    return collection.strip().lower() in STOCK_COLLECTION_NAMES
