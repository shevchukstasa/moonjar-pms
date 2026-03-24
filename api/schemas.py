"""
Moonjar PMS — Pydantic schemas (auto-generated).
Create / Update / Response for each database model.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class FactoryCreate(BaseModel):
    name: str
    location: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    settings: Optional[dict] = None
    timezone: Optional[str] = None
    masters_group_chat_id: Optional[int] = None
    purchaser_chat_id: Optional[int] = None
    telegram_language: Optional[str] = None
    receiving_approval_mode: Optional[str] = None
    kiln_constants_mode: Optional[str] = None
    rotation_rules: Optional[dict] = None
    served_locations: Optional[list] = None
    is_active: Optional[bool] = None


class FactoryUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    settings: Optional[dict] = None
    timezone: Optional[str] = None
    masters_group_chat_id: Optional[int] = None
    purchaser_chat_id: Optional[int] = None
    telegram_language: Optional[str] = None
    receiving_approval_mode: Optional[str] = None
    kiln_constants_mode: Optional[str] = None
    rotation_rules: Optional[dict] = None
    served_locations: Optional[list] = None
    is_active: Optional[bool] = None


class FactoryResponse(BaseModel):
    id: UUID
    name: str
    location: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    settings: Optional[dict] = None
    timezone: Optional[str] = "Asia/Makassar"
    masters_group_chat_id: Optional[int] = None
    purchaser_chat_id: Optional[int] = None
    telegram_language: Optional[str] = "id"
    receiving_approval_mode: Optional[str] = "all"
    kiln_constants_mode: Optional[str] = "manual"
    rotation_rules: Optional[dict] = None
    served_locations: Optional[list] = None
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str
    name: str
    role: str
    google_id: Optional[str] = None
    telegram_user_id: Optional[int] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    failed_login_count: Optional[int] = None
    locked_until: Optional[datetime] = None
    totp_enabled: Optional[bool] = None
    last_password_change: Optional[datetime] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    google_id: Optional[str] = None
    telegram_user_id: Optional[int] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    failed_login_count: Optional[int] = None
    locked_until: Optional[datetime] = None
    totp_enabled: Optional[bool] = None
    last_password_change: Optional[datetime] = None


class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    material_types: Optional[list[str]] = None
    default_lead_time_days: Optional[int] = None
    rating: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    subgroup_ids: Optional[list[UUID]] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    material_types: Optional[list[str]] = None
    default_lead_time_days: Optional[int] = None
    rating: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    subgroup_ids: Optional[list[UUID]] = None


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    material_types: Optional[list[str]] = None
    default_lead_time_days: int
    rating: Optional[float] = None
    notes: Optional[str] = None
    is_active: bool
    subgroup_ids: Optional[list[str]] = None
    subgroup_names: Optional[list[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionCreate(BaseModel):
    name: str


class CollectionUpdate(BaseModel):
    name: Optional[str] = None


class ColorCreate(BaseModel):
    name: str
    code: Optional[str] = None
    is_basic: Optional[bool] = False


class ColorUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_basic: Optional[bool] = None


class FinishingTypeCreate(BaseModel):
    name: str


class FinishingTypeUpdate(BaseModel):
    name: Optional[str] = None


class SizeUpdate(BaseModel):
    name: Optional[str] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    is_custom: Optional[bool] = None


class RecipeCreate(BaseModel):
    name: str
    color_collection: Optional[str] = None
    description: Optional[str] = None
    recipe_type: str = 'product'
    color_type: Optional[str] = None
    specific_gravity: Optional[float] = None
    consumption_spray_ml_per_sqm: Optional[float] = None
    consumption_brush_ml_per_sqm: Optional[float] = None
    is_default: Optional[bool] = None
    client_name: Optional[str] = None
    glaze_settings: Optional[dict] = None
    is_active: Optional[bool] = None
    clone_from_id: Optional[UUID] = None  # Clone materials + firing stages from existing recipe


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    color_collection: Optional[str] = None
    description: Optional[str] = None
    recipe_type: Optional[str] = None
    color_type: Optional[str] = None
    specific_gravity: Optional[float] = None
    consumption_spray_ml_per_sqm: Optional[float] = None
    consumption_brush_ml_per_sqm: Optional[float] = None
    is_default: Optional[bool] = None
    client_name: Optional[str] = None
    glaze_settings: Optional[dict] = None
    is_active: Optional[bool] = None


class RecipeResponse(BaseModel):
    id: UUID
    name: str
    color_collection: Optional[str] = None
    description: Optional[str] = None
    recipe_type: str
    color_type: Optional[str] = None
    specific_gravity: Optional[float] = None
    consumption_spray_ml_per_sqm: Optional[float] = None
    consumption_brush_ml_per_sqm: Optional[float] = None
    is_default: bool = False
    client_name: Optional[str] = None
    glaze_settings: dict = {}
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('glaze_settings', mode='before')
    @classmethod
    def _coerce_glaze_settings(cls, v):
        return v if v is not None else {}


class MaterialCreate(BaseModel):
    name: str
    factory_id: UUID
    balance: Optional[float] = None
    min_balance: Optional[float] = None
    min_balance_recommended: Optional[float] = None
    min_balance_auto: Optional[bool] = None
    avg_daily_consumption: Optional[float] = None
    unit: Optional[str] = None
    material_type: str
    avg_monthly_consumption: Optional[float] = None
    warehouse_section: Optional[str] = None
    supplier_id: Optional[UUID] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    factory_id: Optional[UUID] = None
    balance: Optional[float] = None
    min_balance: Optional[float] = None
    min_balance_recommended: Optional[float] = None
    min_balance_auto: Optional[bool] = None
    avg_daily_consumption: Optional[float] = None
    unit: Optional[str] = None
    material_type: Optional[str] = None
    avg_monthly_consumption: Optional[float] = None
    warehouse_section: Optional[str] = None
    supplier_id: Optional[UUID] = None


class MaterialResponse(BaseModel):
    id: UUID
    name: str
    factory_id: UUID
    balance: float
    min_balance: float
    min_balance_recommended: Optional[float] = None
    min_balance_auto: bool
    avg_daily_consumption: Optional[float] = None
    unit: str
    material_type: str
    avg_monthly_consumption: Optional[float] = None
    warehouse_section: Optional[str] = None
    supplier_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeMaterialBulkItem(BaseModel):
    """Single ingredient in a bulk upsert — grams per 100 g dry mix."""
    material_id: UUID
    quantity_per_unit: float      # grams
    unit: str = 'g_per_100g'
    notes: Optional[str] = None
    # Per-method application rates (optional, set from admin UI)
    spray_rate: Optional[float] = None
    brush_rate: Optional[float] = None
    splash_rate: Optional[float] = None
    silk_screen_rate: Optional[float] = None


class RecipeMaterialsBulkUpdate(BaseModel):
    """Replace all ingredients of a recipe in one call."""
    materials: list[RecipeMaterialBulkItem]


class RecipeMaterialResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    material_id: UUID
    material_name: Optional[str] = None
    material_type: Optional[str] = None
    quantity_per_unit: float
    unit: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BatchCreate(BaseModel):
    resource_id: UUID
    factory_id: UUID
    batch_date: date
    status: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    firing_profile_id: Optional[UUID] = None
    target_temperature: Optional[int] = None


class BatchUpdate(BaseModel):
    resource_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    batch_date: Optional[date] = None
    status: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    firing_profile_id: Optional[UUID] = None
    target_temperature: Optional[int] = None


class BatchResponse(BaseModel):
    id: UUID
    resource_id: UUID
    factory_id: UUID
    batch_date: date
    status: str
    created_by: str
    notes: Optional[str] = None
    firing_profile_id: Optional[UUID] = None
    target_temperature: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    factory_id: UUID
    type: str
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    assigned_role: Optional[str] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    blocking: Optional[bool] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    type: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    assigned_role: Optional[str] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    blocking: Optional[bool] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ProductionStageCreate(BaseModel):
    name: str
    order: int


class ProductionStageUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None


class ProductionStageResponse(BaseModel):
    id: UUID
    name: str
    order: int

    model_config = ConfigDict(from_attributes=True)


class MaterialPurchaseRequestCreate(BaseModel):
    factory_id: UUID
    supplier_id: Optional[UUID] = None
    materials_json: dict
    status: Optional[str] = None
    source: Optional[str] = None
    approved_by: Optional[UUID] = None
    sent_to_chat_at: Optional[datetime] = None
    ordered_at: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    received_quantity_json: Optional[dict] = None
    notes: Optional[str] = None


class MaterialPurchaseRequestUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    materials_json: Optional[dict] = None
    status: Optional[str] = None
    source: Optional[str] = None
    approved_by: Optional[UUID] = None
    sent_to_chat_at: Optional[datetime] = None
    ordered_at: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    received_quantity_json: Optional[dict] = None
    notes: Optional[str] = None


class DefectCauseCreate(BaseModel):
    code: str
    category: str
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DefectCauseUpdate(BaseModel):
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DefectCauseResponse(BaseModel):
    id: UUID
    code: str
    category: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemCardCreate(BaseModel):
    factory_id: UUID
    location: Optional[str] = None
    description: str
    actions: Optional[str] = None
    status: Optional[str] = None
    created_by: Optional[UUID] = None


class ProblemCardUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    location: Optional[str] = None
    description: Optional[str] = None
    actions: Optional[str] = None
    status: Optional[str] = None
    created_by: Optional[UUID] = None


class ProblemCardResponse(BaseModel):
    id: UUID
    factory_id: UUID
    location: Optional[str] = None
    description: str
    actions: Optional[str] = None
    status: str
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrindingStockCreate(BaseModel):
    factory_id: UUID
    color: str
    size: str
    quantity: int
    source_order_id: Optional[UUID] = None
    source_position_id: Optional[UUID] = None
    status: Optional[str] = None


class GrindingStockResponse(BaseModel):
    id: UUID
    factory_id: UUID
    color: str
    size: str
    quantity: int
    source_order_id: Optional[UUID] = None
    source_position_id: Optional[UUID] = None
    status: str
    decided_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrindingStockDecision(BaseModel):
    decision: str  # 'grinding', 'pending', 'sent_to_mana'
    notes: Optional[str] = None


class TpsParameterCreate(BaseModel):
    factory_id: UUID
    stage: str
    metric_name: str
    target_value: float
    tolerance_percent: Optional[float] = None
    unit: Optional[str] = None


class TpsParameterUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    stage: Optional[str] = None
    metric_name: Optional[str] = None
    target_value: Optional[float] = None
    tolerance_percent: Optional[float] = None
    unit: Optional[str] = None


class KilnConstantCreate(BaseModel):
    constant_name: str
    value: float
    unit: Optional[str] = None
    description: Optional[str] = None
    updated_by: Optional[UUID] = None


class KilnConstantUpdate(BaseModel):
    constant_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    updated_by: Optional[UUID] = None


class KilnConstantResponse(BaseModel):
    id: UUID
    constant_name: str
    value: float
    unit: Optional[str] = None
    description: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    factory_id: Optional[UUID] = None
    type: str
    title: str
    message: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDashboardAccessCreate(BaseModel):
    user_id: UUID
    dashboard_type: str
    granted_by: UUID
    granted_at: Optional[datetime] = None


class UserDashboardAccessUpdate(BaseModel):
    user_id: Optional[UUID] = None
    dashboard_type: Optional[str] = None
    granted_by: Optional[UUID] = None
    granted_at: Optional[datetime] = None


class UserDashboardAccessResponse(BaseModel):
    id: UUID
    user_id: UUID
    dashboard_type: str
    granted_by: UUID
    granted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceCreate(BaseModel):
    user_id: UUID
    category: str
    channel: Optional[str] = None


class NotificationPreferenceUpdate(BaseModel):
    user_id: Optional[UUID] = None
    category: Optional[str] = None
    channel: Optional[str] = None


class NotificationPreferenceResponse(BaseModel):
    id: UUID
    user_id: UUID
    category: str
    channel: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialEntryCreate(BaseModel):
    factory_id: UUID
    entry_type: str
    category: str
    amount: float
    currency: Optional[str] = None
    description: Optional[str] = None
    entry_date: date
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    created_by: UUID


class FinancialEntryUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    entry_type: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    entry_date: Optional[date] = None
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    created_by: Optional[UUID] = None


class FinancialEntryResponse(BaseModel):
    id: UUID
    factory_id: UUID
    entry_type: str
    category: str
    amount: float
    currency: str
    description: Optional[str] = None
    entry_date: date
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseSectionCreate(BaseModel):
    factory_id: Optional[UUID] = None
    code: str
    name: str
    description: Optional[str] = None
    managed_by: Optional[UUID] = None
    warehouse_type: str = 'section'
    display_order: int = 0
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class WarehouseSectionUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    managed_by: Optional[UUID] = None
    warehouse_type: Optional[str] = None
    display_order: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class WarehouseSectionResponse(BaseModel):
    id: UUID
    factory_id: Optional[UUID] = None
    code: str
    name: str
    description: Optional[str] = None
    managed_by: Optional[UUID] = None
    managed_by_name: Optional[str] = None
    warehouse_type: str = 'section'
    display_order: int = 0
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryReconciliationCreate(BaseModel):
    factory_id: UUID
    section_id: Optional[UUID] = None
    status: Optional[str] = None
    started_by: UUID
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class InventoryReconciliationUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    section_id: Optional[UUID] = None
    status: Optional[str] = None
    started_by: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class InventoryReconciliationResponse(BaseModel):
    id: UUID
    factory_id: UUID
    section_id: Optional[UUID] = None
    status: str
    started_by: UUID
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QmBlockCreate(BaseModel):
    factory_id: UUID
    block_type: str
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    reason: str
    severity: Optional[str] = None
    photo_urls: Optional[dict] = None
    blocked_by: UUID
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class QmBlockUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    block_type: Optional[str] = None
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    reason: Optional[str] = None
    severity: Optional[str] = None
    photo_urls: Optional[dict] = None
    blocked_by: Optional[UUID] = None
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class QmBlockResponse(BaseModel):
    id: UUID
    factory_id: UUID
    block_type: str
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    reason: str
    severity: str
    photo_urls: Optional[dict] = None
    blocked_by: UUID
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KilnLoadingRuleCreate(BaseModel):
    kiln_id: UUID
    rules: Optional[dict] = None


class KilnLoadingRuleUpdate(BaseModel):
    kiln_id: Optional[UUID] = None
    rules: Optional[dict] = None


class KilnLoadingRuleResponse(BaseModel):
    id: UUID
    kiln_id: UUID
    rules: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KilnFiringScheduleCreate(BaseModel):
    kiln_id: UUID
    name: str
    schedule_data: Optional[dict] = None
    is_default: Optional[bool] = None


class KilnFiringScheduleUpdate(BaseModel):
    kiln_id: Optional[UUID] = None
    name: Optional[str] = None
    schedule_data: Optional[dict] = None
    is_default: Optional[bool] = None


class KilnFiringScheduleResponse(BaseModel):
    id: UUID
    kiln_id: UUID
    name: str
    schedule_data: dict
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IpAllowlistCreate(BaseModel):
    cidr: str
    scope: str
    description: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: UUID


# --- Firing Profiles ---

class FiringProfileCreate(BaseModel):
    name: str
    temperature_group_id: Optional[UUID] = None
    product_type: Optional[str] = None
    collection: Optional[str] = None
    thickness_min_mm: Optional[float] = None
    thickness_max_mm: Optional[float] = None
    target_temperature: int
    total_duration_hours: float
    stages: Optional[list] = None
    match_priority: Optional[int] = None
    is_default: Optional[bool] = None


class FiringProfileUpdate(BaseModel):
    name: Optional[str] = None
    temperature_group_id: Optional[UUID] = None
    product_type: Optional[str] = None
    collection: Optional[str] = None
    thickness_min_mm: Optional[float] = None
    thickness_max_mm: Optional[float] = None
    target_temperature: Optional[int] = None
    total_duration_hours: Optional[float] = None
    stages: Optional[list] = None
    match_priority: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class FiringProfileResponse(BaseModel):
    id: UUID
    name: str
    temperature_group_id: Optional[UUID] = None
    temperature_group_name: Optional[str] = None
    product_type: Optional[str] = None
    collection: Optional[str] = None
    thickness_min_mm: Optional[float] = None
    thickness_max_mm: Optional[float] = None
    target_temperature: int
    total_duration_hours: float
    stages: list
    match_priority: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FiringProfileMatchRequest(BaseModel):
    product_type: str
    collection: Optional[str] = None
    thickness_mm: float


# --- Recipe Firing Stages ---

class RecipeFiringStageCreate(BaseModel):
    stage_number: int = 1
    firing_profile_id: Optional[UUID] = None
    requires_glazing_before: bool = True
    description: Optional[str] = None


class RecipeFiringStageResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    stage_number: int
    firing_profile_id: Optional[UUID] = None
    requires_glazing_before: bool
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeFiringStagesBulkUpdate(BaseModel):
    """Replace all firing stages for a recipe."""
    stages: list[RecipeFiringStageCreate]


# ── ManaShipment ─────────────────────────────────────────────────

class ManaShipmentUpdate(BaseModel):
    notes: Optional[str] = None

class ManaShipmentResponse(BaseModel):
    id: UUID
    factory_id: UUID
    items_json: list[dict]
    status: str
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
