"""
Moonjar PMS — Pydantic schemas (auto-generated).
Create / Update / Response for each database model.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Pagination wrapper ---

class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    per_page: int = 50


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
    require_pm_approval_receiving: Optional[bool] = None
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
    require_pm_approval_receiving: Optional[bool] = None
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
    require_pm_approval_receiving: Optional[bool] = False
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


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    google_id: Optional[str] = None
    telegram_user_id: Optional[int] = None
    language: Optional[str] = "en"
    is_active: Optional[bool] = True
    failed_login_count: Optional[int] = 0
    locked_until: Optional[datetime] = None
    totp_enabled: Optional[bool] = False
    last_password_change: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserFactoryCreate(BaseModel):
    user_id: UUID
    factory_id: UUID


class UserFactoryUpdate(BaseModel):
    user_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None


class UserFactoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    factory_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class SupplierLeadTimeCreate(BaseModel):
    supplier_id: UUID
    material_type: str
    default_lead_time_days: int
    avg_actual_lead_time_days: Optional[float] = None
    last_updated: Optional[datetime] = None
    sample_count: Optional[int] = None


class SupplierLeadTimeUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    material_type: Optional[str] = None
    default_lead_time_days: Optional[int] = None
    avg_actual_lead_time_days: Optional[float] = None
    last_updated: Optional[datetime] = None
    sample_count: Optional[int] = None


class SupplierLeadTimeResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    material_type: str
    default_lead_time_days: int
    avg_actual_lead_time_days: Optional[float] = None
    last_updated: Optional[datetime] = None
    sample_count: int

    model_config = ConfigDict(from_attributes=True)


class CollectionCreate(BaseModel):
    name: str


class CollectionUpdate(BaseModel):
    name: Optional[str] = None


class CollectionResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ColorCreate(BaseModel):
    name: str
    code: Optional[str] = None
    is_basic: Optional[bool] = False


class ColorUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_basic: Optional[bool] = None


class ColorResponse(BaseModel):
    id: UUID
    name: str
    code: Optional[str] = None
    is_basic: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationTypeCreate(BaseModel):
    name: str


class ApplicationTypeUpdate(BaseModel):
    name: Optional[str] = None


class ApplicationTypeResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlacesOfApplicationCreate(BaseModel):
    code: str
    name: str


class PlacesOfApplicationUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class PlacesOfApplicationResponse(BaseModel):
    id: UUID
    code: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinishingTypeCreate(BaseModel):
    name: str


class FinishingTypeUpdate(BaseModel):
    name: Optional[str] = None


class FinishingTypeResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SizeCreate(BaseModel):
    name: str
    width_mm: int
    height_mm: int
    is_custom: Optional[bool] = None


class SizeUpdate(BaseModel):
    name: Optional[str] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    is_custom: Optional[bool] = None


class SizeResponse(BaseModel):
    id: UUID
    name: str
    width_mm: int
    height_mm: int
    is_custom: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReferenceAuditLogCreate(BaseModel):
    table_name: str
    record_id: UUID
    action: str
    old_values_json: Optional[dict] = None
    new_values_json: Optional[dict] = None
    changed_by: Optional[UUID] = None
    changed_at: Optional[datetime] = None


class ReferenceAuditLogUpdate(BaseModel):
    table_name: Optional[str] = None
    record_id: Optional[UUID] = None
    action: Optional[str] = None
    old_values_json: Optional[dict] = None
    new_values_json: Optional[dict] = None
    changed_by: Optional[UUID] = None
    changed_at: Optional[datetime] = None


class ReferenceAuditLogResponse(BaseModel):
    id: UUID
    table_name: str
    record_id: UUID
    action: str
    old_values_json: Optional[dict] = None
    new_values_json: Optional[dict] = None
    changed_by: Optional[UUID] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionOrderCreate(BaseModel):
    order_number: str
    client: str
    client_location: Optional[str] = None
    sales_manager_name: Optional[str] = None
    sales_manager_contact: Optional[str] = None
    factory_id: UUID
    document_date: Optional[date] = None
    production_received_date: Optional[date] = None
    final_deadline: Optional[date] = None
    schedule_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    status: Optional[str] = None
    status_override: Optional[bool] = None
    sales_status: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    sales_payload_json: Optional[dict] = None
    mandatory_qc: Optional[bool] = None
    notes: Optional[str] = None


class ProductionOrderUpdate(BaseModel):
    order_number: Optional[str] = None
    client: Optional[str] = None
    client_location: Optional[str] = None
    sales_manager_name: Optional[str] = None
    sales_manager_contact: Optional[str] = None
    factory_id: Optional[UUID] = None
    document_date: Optional[date] = None
    production_received_date: Optional[date] = None
    final_deadline: Optional[date] = None
    schedule_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    status: Optional[str] = None
    status_override: Optional[bool] = None
    sales_status: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    sales_payload_json: Optional[dict] = None
    mandatory_qc: Optional[bool] = None
    notes: Optional[str] = None


class ProductionOrderResponse(BaseModel):
    id: UUID
    order_number: str
    client: str
    client_location: Optional[str] = None
    sales_manager_name: Optional[str] = None
    sales_manager_contact: Optional[str] = None
    factory_id: UUID
    document_date: Optional[date] = None
    production_received_date: Optional[date] = None
    final_deadline: Optional[date] = None
    schedule_deadline: Optional[date] = None
    desired_delivery_date: Optional[date] = None
    status: str
    status_override: bool
    sales_status: Optional[str] = None
    source: str
    external_id: Optional[str] = None
    sales_payload_json: Optional[dict] = None
    mandatory_qc: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionOrderItemCreate(BaseModel):
    order_id: UUID
    color: str
    size: str
    application: Optional[str] = None
    finishing: Optional[str] = None
    thickness: Optional[float] = None
    quantity_pcs: int
    quantity_sqm: Optional[float] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: Optional[str] = None


class ProductionOrderItemUpdate(BaseModel):
    order_id: Optional[UUID] = None
    color: Optional[str] = None
    size: Optional[str] = None
    application: Optional[str] = None
    finishing: Optional[str] = None
    thickness: Optional[float] = None
    quantity_pcs: Optional[int] = None
    quantity_sqm: Optional[float] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: Optional[str] = None


class ProductionOrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    color: str
    size: str
    application: Optional[str] = None
    finishing: Optional[str] = None
    thickness: float
    quantity_pcs: int
    quantity_sqm: Optional[float] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesWebhookEventCreate(BaseModel):
    event_id: str
    payload_json: dict
    processed: Optional[bool] = None
    error_message: Optional[str] = None


class SalesWebhookEventUpdate(BaseModel):
    event_id: Optional[str] = None
    payload_json: Optional[dict] = None
    processed: Optional[bool] = None
    error_message: Optional[str] = None


class SalesWebhookEventResponse(BaseModel):
    id: UUID
    event_id: str
    payload_json: dict
    processed: bool
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionOrderChangeRequestCreate(BaseModel):
    order_id: UUID
    change_type: Optional[str] = None
    diff_json: dict
    status: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ProductionOrderChangeRequestUpdate(BaseModel):
    order_id: Optional[UUID] = None
    change_type: Optional[str] = None
    diff_json: Optional[dict] = None
    status: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ProductionOrderChangeRequestResponse(BaseModel):
    id: UUID
    order_id: UUID
    change_type: str
    diff_json: dict
    status: str
    reviewed_by: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductionOrderStatusLogCreate(BaseModel):
    order_id: UUID
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[UUID] = None
    is_override: Optional[bool] = None
    notes: Optional[str] = None


class ProductionOrderStatusLogUpdate(BaseModel):
    order_id: Optional[UUID] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    changed_by: Optional[UUID] = None
    is_override: Optional[bool] = None
    notes: Optional[str] = None


class ProductionOrderStatusLogResponse(BaseModel):
    id: UUID
    order_id: UUID
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[UUID] = None
    is_override: bool
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    glaze_settings: Optional[dict] = None
    is_active: Optional[bool] = None


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
    glaze_settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class RecipeMaterialCreate(BaseModel):
    recipe_id: UUID
    material_id: UUID
    quantity_per_unit: float
    unit: Optional[str] = None
    notes: Optional[str] = None


class RecipeMaterialUpdate(BaseModel):
    recipe_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    quantity_per_unit: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class RecipeMaterialBulkItem(BaseModel):
    """Single ingredient in a bulk upsert — grams per 100 g dry mix."""
    material_id: UUID
    quantity_per_unit: float      # grams
    unit: str = 'g_per_100g'
    notes: Optional[str] = None


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


class RecipeKilnConfigCreate(BaseModel):
    recipe_id: UUID
    firing_temperature: Optional[int] = None
    firing_duration_hours: Optional[float] = None
    two_stage_firing: Optional[bool] = None
    special_instructions: Optional[str] = None


class RecipeKilnConfigUpdate(BaseModel):
    recipe_id: Optional[UUID] = None
    firing_temperature: Optional[int] = None
    firing_duration_hours: Optional[float] = None
    two_stage_firing: Optional[bool] = None
    special_instructions: Optional[str] = None


class RecipeKilnConfigResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    firing_temperature: Optional[int] = None
    firing_duration_hours: Optional[float] = None
    two_stage_firing: bool
    special_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceCreate(BaseModel):
    name: str
    resource_type: str
    factory_id: UUID
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None
    num_levels: Optional[int] = None
    status: Optional[str] = None
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: Optional[bool] = None
    kiln_coefficient: Optional[float] = None
    kiln_type: Optional[str] = None
    is_active: Optional[bool] = None


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    resource_type: Optional[str] = None
    factory_id: Optional[UUID] = None
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None
    num_levels: Optional[int] = None
    status: Optional[str] = None
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: Optional[bool] = None
    kiln_coefficient: Optional[float] = None
    kiln_type: Optional[str] = None
    is_active: Optional[bool] = None


class ResourceResponse(BaseModel):
    id: UUID
    name: str
    resource_type: Optional[str] = None
    factory_id: Optional[UUID] = None
    capacity_sqm: Optional[float] = None
    capacity_pcs: Optional[int] = None
    num_levels: Optional[int] = None
    status: Optional[str] = "active"
    kiln_dimensions_cm: Optional[dict] = None
    kiln_working_area_cm: Optional[dict] = None
    kiln_multi_level: Optional[bool] = None
    kiln_coefficient: Optional[float] = None
    kiln_type: Optional[str] = None
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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


class ScheduleSlotCreate(BaseModel):
    resource_id: UUID
    start_at: datetime
    end_at: datetime
    batch_id: Optional[UUID] = None
    status: Optional[str] = None


class ScheduleSlotUpdate(BaseModel):
    resource_id: Optional[UUID] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    batch_id: Optional[UUID] = None
    status: Optional[str] = None


class ScheduleSlotResponse(BaseModel):
    id: UUID
    resource_id: UUID
    start_at: datetime
    end_at: datetime
    batch_id: Optional[UUID] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderPositionCreate(BaseModel):
    order_id: UUID
    order_item_id: UUID
    parent_position_id: Optional[UUID] = None
    factory_id: UUID
    status: Optional[str] = None
    batch_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    placement_position: Optional[str] = None
    placement_level: Optional[int] = None
    delay_hours: Optional[float] = None
    reservation_at: Optional[datetime] = None
    materials_written_off_at: Optional[datetime] = None
    quantity: int
    quantity_with_defect_margin: Optional[int] = None
    color: str
    size: str
    application: Optional[str] = None
    finishing: Optional[str] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: Optional[str] = None
    shape: Optional[str] = None
    thickness_mm: Optional[float] = None
    recipe_id: Optional[UUID] = None
    mandatory_qc: Optional[bool] = None
    split_category: Optional[str] = None
    is_merged: Optional[bool] = None
    priority_order: Optional[int] = None
    firing_round: Optional[int] = None


class OrderPositionUpdate(BaseModel):
    order_id: Optional[UUID] = None
    order_item_id: Optional[UUID] = None
    parent_position_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    status: Optional[str] = None
    batch_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    placement_position: Optional[str] = None
    placement_level: Optional[int] = None
    delay_hours: Optional[float] = None
    reservation_at: Optional[datetime] = None
    materials_written_off_at: Optional[datetime] = None
    quantity: Optional[int] = None
    quantity_with_defect_margin: Optional[int] = None
    color: Optional[str] = None
    size: Optional[str] = None
    application: Optional[str] = None
    finishing: Optional[str] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: Optional[str] = None
    shape: Optional[str] = None
    thickness_mm: Optional[float] = None
    recipe_id: Optional[UUID] = None
    mandatory_qc: Optional[bool] = None
    split_category: Optional[str] = None
    is_merged: Optional[bool] = None
    priority_order: Optional[int] = None
    firing_round: Optional[int] = None


class OrderPositionResponse(BaseModel):
    id: UUID
    order_id: UUID
    order_item_id: UUID
    parent_position_id: Optional[UUID] = None
    factory_id: UUID
    status: str
    batch_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    placement_position: Optional[str] = None
    placement_level: Optional[int] = None
    delay_hours: Optional[float] = None
    reservation_at: Optional[datetime] = None
    materials_written_off_at: Optional[datetime] = None
    quantity: int
    quantity_with_defect_margin: Optional[int] = None
    color: str
    size: str
    application: Optional[str] = None
    finishing: Optional[str] = None
    collection: Optional[str] = None
    application_type: Optional[str] = None
    place_of_application: Optional[str] = None
    product_type: str
    shape: Optional[str] = None
    thickness_mm: float
    recipe_id: Optional[UUID] = None
    mandatory_qc: bool
    split_category: Optional[str] = None
    is_merged: bool
    priority_order: Optional[int] = None
    firing_round: int = 1
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


class TaskResponse(BaseModel):
    id: UUID
    factory_id: UUID
    type: str
    status: str
    assigned_to: Optional[UUID] = None
    assigned_role: Optional[str] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    blocking: bool
    description: Optional[str] = None
    priority: int
    due_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class OrderStageHistoryCreate(BaseModel):
    order_id: UUID
    stage_id: UUID
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None


class OrderStageHistoryUpdate(BaseModel):
    order_id: Optional[UUID] = None
    stage_id: Optional[UUID] = None
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None


class OrderStageHistoryResponse(BaseModel):
    id: UUID
    order_id: UUID
    stage_id: UUID
    entered_at: datetime
    exited_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MaterialTransactionCreate(BaseModel):
    material_id: UUID
    type: str
    quantity: float
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None


class MaterialTransactionUpdate(BaseModel):
    material_id: Optional[UUID] = None
    type: Optional[str] = None
    quantity: Optional[float] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None


class MaterialTransactionResponse(BaseModel):
    id: UUID
    material_id: UUID
    type: str
    quantity: float
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime

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


class MaterialPurchaseRequestResponse(BaseModel):
    id: UUID
    factory_id: UUID
    supplier_id: Optional[UUID] = None
    materials_json: dict
    status: str
    source: str
    approved_by: Optional[UUID] = None
    sent_to_chat_at: Optional[datetime] = None
    ordered_at: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    received_quantity_json: Optional[dict] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class QualityCheckCreate(BaseModel):
    position_id: UUID
    factory_id: UUID
    operation_type: Optional[str] = None
    stage: str
    result: str
    defect_cause_id: Optional[UUID] = None
    photos: Optional[list[str]] = None
    notes: Optional[str] = None
    checked_by: Optional[UUID] = None


class QualityCheckUpdate(BaseModel):
    position_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    operation_type: Optional[str] = None
    stage: Optional[str] = None
    result: Optional[str] = None
    defect_cause_id: Optional[UUID] = None
    photos: Optional[list[str]] = None
    notes: Optional[str] = None
    checked_by: Optional[UUID] = None


class QualityCheckResponse(BaseModel):
    id: UUID
    position_id: UUID
    factory_id: UUID
    operation_type: Optional[str] = None
    stage: str
    result: str
    defect_cause_id: Optional[UUID] = None
    photos: Optional[list[str]] = None
    notes: Optional[str] = None
    checked_by: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualityAssignmentConfigCreate(BaseModel):
    factory_id: UUID
    stage: str
    base_percentage: Optional[float] = None
    increase_on_defect_percentage: Optional[float] = None
    current_percentage: Optional[float] = None


class QualityAssignmentConfigUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    stage: Optional[str] = None
    base_percentage: Optional[float] = None
    increase_on_defect_percentage: Optional[float] = None
    current_percentage: Optional[float] = None


class QualityAssignmentConfigResponse(BaseModel):
    id: UUID
    factory_id: UUID
    stage: str
    base_percentage: float
    increase_on_defect_percentage: float
    current_percentage: float
    updated_at: datetime

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


class DefectRecordCreate(BaseModel):
    factory_id: UUID
    stage: str
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    defect_type: str
    quantity: int
    outcome: str
    reported_by: Optional[UUID] = None
    reported_via: Optional[str] = None
    photos: Optional[list[str]] = None
    notes: Optional[str] = None
    date: Optional[date] = None


class DefectRecordUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    stage: Optional[str] = None
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    defect_type: Optional[str] = None
    quantity: Optional[int] = None
    outcome: Optional[str] = None
    reported_by: Optional[UUID] = None
    reported_via: Optional[str] = None
    photos: Optional[list[str]] = None
    notes: Optional[str] = None
    date: Optional[date] = None


class DefectRecordResponse(BaseModel):
    id: UUID
    factory_id: UUID
    stage: str
    position_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    supplier_id: Optional[UUID] = None
    defect_type: str
    quantity: int
    outcome: str
    reported_by: Optional[UUID] = None
    reported_via: str
    photos: Optional[list[str]] = None
    notes: Optional[str] = None
    date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoneDefectCoefficientCreate(BaseModel):
    factory_id: UUID
    stone_type: str
    supplier_id: Optional[UUID] = None
    coefficient: Optional[float] = None
    sample_size: Optional[int] = None
    last_updated: Optional[datetime] = None
    calculation_period_days: Optional[int] = None


class StoneDefectCoefficientUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    stone_type: Optional[str] = None
    supplier_id: Optional[UUID] = None
    coefficient: Optional[float] = None
    sample_size: Optional[int] = None
    last_updated: Optional[datetime] = None
    calculation_period_days: Optional[int] = None


class StoneDefectCoefficientResponse(BaseModel):
    id: UUID
    factory_id: UUID
    stone_type: str
    supplier_id: Optional[UUID] = None
    coefficient: float
    sample_size: int
    last_updated: Optional[datetime] = None
    calculation_period_days: int

    model_config = ConfigDict(from_attributes=True)


class GrindingStockCreate(BaseModel):
    factory_id: UUID
    color: str
    size: str
    quantity: int
    source_order_id: Optional[UUID] = None
    source_position_id: Optional[UUID] = None
    status: Optional[str] = None


class GrindingStockUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    color: Optional[str] = None
    size: Optional[str] = None
    quantity: Optional[int] = None
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepairQueueCreate(BaseModel):
    factory_id: UUID
    color: str
    size: str
    quantity: int
    defect_type: Optional[str] = None
    source_order_id: Optional[UUID] = None
    source_position_id: Optional[UUID] = None
    status: Optional[str] = None
    repaired_at: Optional[datetime] = None


class RepairQueueUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    color: Optional[str] = None
    size: Optional[str] = None
    quantity: Optional[int] = None
    defect_type: Optional[str] = None
    source_order_id: Optional[UUID] = None
    source_position_id: Optional[UUID] = None
    status: Optional[str] = None
    repaired_at: Optional[datetime] = None


class RepairQueueResponse(BaseModel):
    id: UUID
    factory_id: UUID
    color: str
    size: str
    quantity: int
    defect_type: Optional[str] = None
    source_order_id: Optional[UUID] = None
    source_position_id: Optional[UUID] = None
    status: str
    created_at: datetime
    repaired_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManuShipmentCreate(BaseModel):
    factory_id: UUID
    items_json: dict
    status: Optional[str] = None
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    notes: Optional[str] = None


class ManuShipmentUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    items_json: Optional[dict] = None
    status: Optional[str] = None
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    notes: Optional[str] = None


class ManuShipmentResponse(BaseModel):
    id: UUID
    factory_id: UUID
    items_json: dict
    status: str
    confirmed_by: Optional[UUID] = None
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SurplusDispositionCreate(BaseModel):
    factory_id: UUID
    order_id: UUID
    position_id: UUID
    surplus_quantity: int
    disposition_type: str
    size: str
    color: str
    is_base_color: Optional[bool] = None
    task_id: Optional[UUID] = None


class SurplusDispositionUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    position_id: Optional[UUID] = None
    surplus_quantity: Optional[int] = None
    disposition_type: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    is_base_color: Optional[bool] = None
    task_id: Optional[UUID] = None


class SurplusDispositionResponse(BaseModel):
    id: UUID
    factory_id: UUID
    order_id: UUID
    position_id: UUID
    surplus_quantity: int
    disposition_type: str
    size: str
    color: str
    is_base_color: bool
    task_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CastersBoxCreate(BaseModel):
    factory_id: UUID
    color: str
    size: str
    quantity: int
    source_order_id: Optional[UUID] = None
    added_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    removed_reason: Optional[str] = None
    notes: Optional[str] = None


class CastersBoxUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    color: Optional[str] = None
    size: Optional[str] = None
    quantity: Optional[int] = None
    source_order_id: Optional[UUID] = None
    added_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    removed_reason: Optional[str] = None
    notes: Optional[str] = None


class CastersBoxResponse(BaseModel):
    id: UUID
    factory_id: UUID
    color: str
    size: str
    quantity: int
    source_order_id: Optional[UUID] = None
    added_at: datetime
    removed_at: Optional[datetime] = None
    removed_reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderPackingPhotoCreate(BaseModel):
    order_id: UUID
    position_id: Optional[UUID] = None
    photo_url: str
    uploaded_by: Optional[UUID] = None
    uploaded_at: Optional[datetime] = None
    notes: Optional[str] = None


class OrderPackingPhotoUpdate(BaseModel):
    order_id: Optional[UUID] = None
    position_id: Optional[UUID] = None
    photo_url: Optional[str] = None
    uploaded_by: Optional[UUID] = None
    uploaded_at: Optional[datetime] = None
    notes: Optional[str] = None


class OrderPackingPhotoResponse(BaseModel):
    id: UUID
    order_id: UUID
    position_id: Optional[UUID] = None
    photo_url: str
    uploaded_by: Optional[UUID] = None
    uploaded_at: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierDefectReportCreate(BaseModel):
    supplier_id: UUID
    factory_id: UUID
    period_start: date
    period_end: date
    total_inspected: Optional[int] = None
    total_defective: Optional[int] = None
    defect_percentage: Optional[float] = None
    report_file_url: Optional[str] = None
    sent_at: Optional[datetime] = None


class SupplierDefectReportUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    total_inspected: Optional[int] = None
    total_defective: Optional[int] = None
    defect_percentage: Optional[float] = None
    report_file_url: Optional[str] = None
    sent_at: Optional[datetime] = None


class SupplierDefectReportResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    factory_id: UUID
    period_start: date
    period_end: date
    total_inspected: int
    total_defective: int
    defect_percentage: float
    report_file_url: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StageReconciliationLogCreate(BaseModel):
    factory_id: UUID
    batch_id: Optional[UUID] = None
    stage_from: str
    stage_to: str
    input_count: int
    output_good: Optional[int] = None
    output_defect: Optional[int] = None
    output_write_off: Optional[int] = None
    discrepancy: Optional[int] = None
    is_balanced: Optional[bool] = None
    checked_at: Optional[datetime] = None
    alert_sent: Optional[bool] = None


class StageReconciliationLogUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    stage_from: Optional[str] = None
    stage_to: Optional[str] = None
    input_count: Optional[int] = None
    output_good: Optional[int] = None
    output_defect: Optional[int] = None
    output_write_off: Optional[int] = None
    discrepancy: Optional[int] = None
    is_balanced: Optional[bool] = None
    checked_at: Optional[datetime] = None
    alert_sent: Optional[bool] = None


class StageReconciliationLogResponse(BaseModel):
    id: UUID
    factory_id: UUID
    batch_id: Optional[UUID] = None
    stage_from: str
    stage_to: str
    input_count: int
    output_good: int
    output_defect: int
    output_write_off: int
    discrepancy: int
    is_balanced: bool
    checked_at: datetime
    alert_sent: bool

    model_config = ConfigDict(from_attributes=True)


class ShiftCreate(BaseModel):
    factory_id: UUID
    shift_number: int
    shift_name: Optional[str] = None
    start_time: time
    end_time: time
    days_of_week: Optional[list[int]] = None
    is_active: Optional[bool] = None


class ShiftUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    shift_number: Optional[int] = None
    shift_name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    days_of_week: Optional[list[int]] = None
    is_active: Optional[bool] = None


class ShiftResponse(BaseModel):
    id: UUID
    factory_id: UUID
    shift_number: int
    shift_name: Optional[str] = None
    start_time: time
    end_time: time
    days_of_week: Optional[list[int]] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


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


class TpsParameterResponse(BaseModel):
    id: UUID
    factory_id: UUID
    stage: str
    metric_name: str
    target_value: float
    tolerance_percent: float
    unit: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TpsShiftMetricCreate(BaseModel):
    factory_id: UUID
    shift: int
    date: date
    stage: str
    planned_output: float
    actual_output: float
    actual_output_pcs: Optional[int] = None
    deviation_percent: Optional[float] = None
    defect_rate: Optional[float] = None
    downtime_minutes: Optional[float] = None
    cycle_time_minutes: Optional[float] = None
    oee_percent: Optional[float] = None
    takt_time_minutes: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TpsShiftMetricUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    shift: Optional[int] = None
    date: Optional[date] = None
    stage: Optional[str] = None
    planned_output: Optional[float] = None
    actual_output: Optional[float] = None
    actual_output_pcs: Optional[int] = None
    deviation_percent: Optional[float] = None
    defect_rate: Optional[float] = None
    downtime_minutes: Optional[float] = None
    cycle_time_minutes: Optional[float] = None
    oee_percent: Optional[float] = None
    takt_time_minutes: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TpsShiftMetricResponse(BaseModel):
    id: UUID
    factory_id: UUID
    shift: int
    date: date
    stage: str
    planned_output: float
    actual_output: float
    actual_output_pcs: int
    deviation_percent: float
    defect_rate: Optional[float] = None
    downtime_minutes: Optional[float] = None
    cycle_time_minutes: Optional[float] = None
    oee_percent: Optional[float] = None
    takt_time_minutes: Optional[float] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TpsDeviationCreate(BaseModel):
    factory_id: UUID
    shift: int
    stage: str
    deviation_type: str
    description: str
    severity: Optional[str] = None
    resolved: Optional[bool] = None


class TpsDeviationUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    shift: Optional[int] = None
    stage: Optional[str] = None
    deviation_type: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    resolved: Optional[bool] = None


class TpsDeviationResponse(BaseModel):
    id: UUID
    factory_id: UUID
    shift: int
    stage: str
    deviation_type: str
    description: str
    severity: str
    resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessStepCreate(BaseModel):
    name: str
    factory_id: UUID
    norm_time_minutes: float
    sequence: int


class ProcessStepUpdate(BaseModel):
    name: Optional[str] = None
    factory_id: Optional[UUID] = None
    norm_time_minutes: Optional[float] = None
    sequence: Optional[int] = None


class ProcessStepResponse(BaseModel):
    id: UUID
    name: str
    factory_id: UUID
    norm_time_minutes: float
    sequence: int

    model_config = ConfigDict(from_attributes=True)


class StandardWorkCreate(BaseModel):
    process_step_id: UUID
    description: str
    time_minutes: float


class StandardWorkUpdate(BaseModel):
    process_step_id: Optional[UUID] = None
    description: Optional[str] = None
    time_minutes: Optional[float] = None


class StandardWorkResponse(BaseModel):
    id: UUID
    process_step_id: UUID
    description: str
    time_minutes: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BottleneckConfigCreate(BaseModel):
    factory_id: UUID
    constraint_resource_id: Optional[UUID] = None
    buffer_target_hours: Optional[float] = None
    rope_limit: Optional[int] = None
    rope_max_days: Optional[int] = None
    rope_min_days: Optional[int] = None
    batch_mode: Optional[str] = None
    current_bottleneck_utilization: Optional[float] = None


class BottleneckConfigUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    constraint_resource_id: Optional[UUID] = None
    buffer_target_hours: Optional[float] = None
    rope_limit: Optional[int] = None
    rope_max_days: Optional[int] = None
    rope_min_days: Optional[int] = None
    batch_mode: Optional[str] = None
    current_bottleneck_utilization: Optional[float] = None


class BottleneckConfigResponse(BaseModel):
    id: UUID
    factory_id: UUID
    constraint_resource_id: Optional[UUID] = None
    buffer_target_hours: float
    rope_limit: Optional[int] = None
    rope_max_days: int
    rope_min_days: int
    batch_mode: str
    current_bottleneck_utilization: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BufferStatusCreate(BaseModel):
    resource_id: UUID
    buffered_positions_count: Optional[int] = None
    buffered_sqm: Optional[float] = None
    buffer_health: Optional[str] = None


class BufferStatusUpdate(BaseModel):
    resource_id: Optional[UUID] = None
    buffered_positions_count: Optional[int] = None
    buffered_sqm: Optional[float] = None
    buffer_health: Optional[str] = None


class BufferStatusResponse(BaseModel):
    id: UUID
    resource_id: UUID
    buffered_positions_count: int
    buffered_sqm: float
    buffer_health: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Kiln Maintenance Types ────────────────────────────────

class KilnMaintenanceTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_hours: float = 2
    requires_empty_kiln: bool = False
    requires_cooled_kiln: bool = False
    requires_power_off: bool = False
    default_interval_days: Optional[int] = None
    is_active: bool = True


class KilnMaintenanceTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[float] = None
    requires_empty_kiln: Optional[bool] = None
    requires_cooled_kiln: Optional[bool] = None
    requires_power_off: Optional[bool] = None
    default_interval_days: Optional[int] = None
    is_active: Optional[bool] = None


class KilnMaintenanceTypeResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    duration_hours: float
    requires_empty_kiln: bool
    requires_cooled_kiln: bool
    requires_power_off: bool
    default_interval_days: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Kiln Maintenance Schedule ─────────────────────────────

class KilnMaintenanceScheduleCreate(BaseModel):
    resource_id: UUID
    maintenance_type: str
    maintenance_type_id: Optional[UUID] = None
    scheduled_date: date
    scheduled_time: Optional[time] = None
    estimated_duration_hours: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    is_recurring: bool = False
    recurrence_interval_days: Optional[int] = None
    requires_empty_kiln: bool = False
    requires_cooled_kiln: bool = False
    requires_power_off: bool = False


class KilnMaintenanceScheduleUpdate(BaseModel):
    resource_id: Optional[UUID] = None
    maintenance_type: Optional[str] = None
    maintenance_type_id: Optional[UUID] = None
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[time] = None
    estimated_duration_hours: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    is_recurring: Optional[bool] = None
    recurrence_interval_days: Optional[int] = None
    requires_empty_kiln: Optional[bool] = None
    requires_cooled_kiln: Optional[bool] = None
    requires_power_off: Optional[bool] = None


class KilnMaintenanceScheduleResponse(BaseModel):
    id: UUID
    resource_id: UUID
    maintenance_type: str
    maintenance_type_id: Optional[UUID] = None
    scheduled_date: date
    scheduled_time: Optional[time] = None
    estimated_duration_hours: Optional[float] = None
    status: str
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    is_recurring: bool = False
    recurrence_interval_days: Optional[int] = None
    requires_empty_kiln: bool = False
    requires_cooled_kiln: bool = False
    requires_power_off: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KilnMaintenanceMaterialCreate(BaseModel):
    maintenance_id: UUID
    material_id: UUID
    required_quantity: float
    in_stock_quantity: Optional[float] = None


class KilnMaintenanceMaterialUpdate(BaseModel):
    maintenance_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    required_quantity: Optional[float] = None
    in_stock_quantity: Optional[float] = None


class KilnMaintenanceMaterialResponse(BaseModel):
    id: UUID
    maintenance_id: UUID
    material_id: UUID
    required_quantity: float
    in_stock_quantity: float

    model_config = ConfigDict(from_attributes=True)


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


class DailyTaskDistributionCreate(BaseModel):
    factory_id: UUID
    distribution_date: date
    glazing_tasks_json: Optional[dict] = None
    kiln_loading_json: Optional[dict] = None
    glaze_recipes_json: Optional[dict] = None
    sent_at: Optional[datetime] = None
    sent_to_chat: Optional[bool] = None
    message_id: Optional[int] = None


class DailyTaskDistributionUpdate(BaseModel):
    factory_id: Optional[UUID] = None
    distribution_date: Optional[date] = None
    glazing_tasks_json: Optional[dict] = None
    kiln_loading_json: Optional[dict] = None
    glaze_recipes_json: Optional[dict] = None
    sent_at: Optional[datetime] = None
    sent_to_chat: Optional[bool] = None
    message_id: Optional[int] = None


class DailyTaskDistributionResponse(BaseModel):
    id: UUID
    factory_id: UUID
    distribution_date: date
    glazing_tasks_json: Optional[dict] = None
    kiln_loading_json: Optional[dict] = None
    glaze_recipes_json: Optional[dict] = None
    sent_at: Optional[datetime] = None
    sent_to_chat: bool
    message_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationCreate(BaseModel):
    user_id: UUID
    factory_id: Optional[UUID] = None
    type: str
    title: str
    message: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    is_read: Optional[bool] = None


class NotificationUpdate(BaseModel):
    user_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    type: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    is_read: Optional[bool] = None


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


class AiChatHistoryCreate(BaseModel):
    user_id: UUID
    messages_json: Optional[dict] = None
    context: Optional[str] = None
    session_name: Optional[str] = None


class AiChatHistoryUpdate(BaseModel):
    user_id: Optional[UUID] = None
    messages_json: Optional[dict] = None
    context: Optional[str] = None
    session_name: Optional[str] = None


class AiChatHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    messages_json: dict
    context: Optional[str] = None
    session_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KilnCalculationLogCreate(BaseModel):
    calculation_type: str
    batch_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    input_json: dict
    output_json: dict
    duration_ms: Optional[int] = None


class KilnCalculationLogUpdate(BaseModel):
    calculation_type: Optional[str] = None
    batch_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    input_json: Optional[dict] = None
    output_json: Optional[dict] = None
    duration_ms: Optional[int] = None


class KilnCalculationLogResponse(BaseModel):
    id: UUID
    calculation_type: str
    batch_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    input_json: dict
    output_json: dict
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerMediaCreate(BaseModel):
    file_id: Optional[str] = None
    file_url: Optional[str] = None
    media_type: str
    telegram_user_id: Optional[int] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    notes: Optional[str] = None


class WorkerMediaUpdate(BaseModel):
    file_id: Optional[str] = None
    file_url: Optional[str] = None
    media_type: Optional[str] = None
    telegram_user_id: Optional[int] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    notes: Optional[str] = None


class WorkerMediaResponse(BaseModel):
    id: UUID
    file_id: Optional[str] = None
    file_url: Optional[str] = None
    media_type: str
    telegram_user_id: Optional[int] = None
    related_order_id: Optional[UUID] = None
    related_position_id: Optional[UUID] = None
    factory_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RagEmbeddingCreate(BaseModel):
    source_table: str
    source_id: UUID
    content_text: str
    embedding: Optional[list[float]] = None
    metadata_json: Optional[dict] = None


class RagEmbeddingUpdate(BaseModel):
    source_table: Optional[str] = None
    source_id: Optional[UUID] = None
    content_text: Optional[str] = None
    embedding: Optional[list[float]] = None
    metadata_json: Optional[dict] = None


class RagEmbeddingResponse(BaseModel):
    id: UUID
    source_table: str
    source_id: UUID
    content_text: str
    embedding: Optional[list[float]] = None
    metadata_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

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


class OrderFinancialCreate(BaseModel):
    order_id: UUID
    total_price: Optional[float] = None
    currency: Optional[str] = None
    cost_estimate: Optional[float] = None
    margin_percent: Optional[float] = None


class OrderFinancialUpdate(BaseModel):
    order_id: Optional[UUID] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None
    cost_estimate: Optional[float] = None
    margin_percent: Optional[float] = None


class OrderFinancialResponse(BaseModel):
    id: UUID
    order_id: UUID
    total_price: Optional[float] = None
    currency: str
    cost_estimate: Optional[float] = None
    margin_percent: Optional[float] = None
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


class InventoryReconciliationItemCreate(BaseModel):
    reconciliation_id: UUID
    material_id: UUID
    system_quantity: float
    actual_quantity: float
    difference: float
    adjustment_applied: Optional[bool] = None


class InventoryReconciliationItemUpdate(BaseModel):
    reconciliation_id: Optional[UUID] = None
    material_id: Optional[UUID] = None
    system_quantity: Optional[float] = None
    actual_quantity: Optional[float] = None
    difference: Optional[float] = None
    adjustment_applied: Optional[bool] = None


class InventoryReconciliationItemResponse(BaseModel):
    id: UUID
    reconciliation_id: UUID
    material_id: UUID
    system_quantity: float
    actual_quantity: float
    difference: float
    adjustment_applied: bool

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


class KilnActualLoadCreate(BaseModel):
    kiln_id: UUID
    batch_id: UUID
    actual_pieces: int
    actual_area_sqm: Optional[float] = None
    calculated_capacity: int
    loading_type: str


class KilnActualLoadUpdate(BaseModel):
    kiln_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None
    actual_pieces: Optional[int] = None
    actual_area_sqm: Optional[float] = None
    calculated_capacity: Optional[int] = None
    loading_type: Optional[str] = None


class KilnActualLoadResponse(BaseModel):
    id: UUID
    kiln_id: UUID
    batch_id: UUID
    actual_pieces: int
    actual_area_sqm: Optional[float] = None
    calculated_capacity: int
    loading_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityAuditLogCreate(BaseModel):
    action: str
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    target_entity: Optional[str] = None
    target_id: Optional[UUID] = None
    details: Optional[dict] = None
    factory_id: Optional[UUID] = None


class SecurityAuditLogUpdate(BaseModel):
    action: Optional[str] = None
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    target_entity: Optional[str] = None
    target_id: Optional[UUID] = None
    details: Optional[dict] = None
    factory_id: Optional[UUID] = None


class SecurityAuditLogResponse(BaseModel):
    id: UUID
    action: str
    actor_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    target_entity: Optional[str] = None
    target_id: Optional[UUID] = None
    details: Optional[dict] = None
    factory_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveSessionCreate(BaseModel):
    user_id: UUID
    token_jti: str
    ip_address: str
    user_agent: Optional[str] = None
    device_label: Optional[str] = None
    expires_at: datetime
    revoked: Optional[bool] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None


class ActiveSessionUpdate(BaseModel):
    user_id: Optional[UUID] = None
    token_jti: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_label: Optional[str] = None
    expires_at: Optional[datetime] = None
    revoked: Optional[bool] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None


class ActiveSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    token_jti: str
    ip_address: str
    user_agent: Optional[str] = None
    device_label: Optional[str] = None
    expires_at: datetime
    revoked: bool
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IpAllowlistCreate(BaseModel):
    cidr: str
    scope: str
    description: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: UUID


class IpAllowlistUpdate(BaseModel):
    cidr: Optional[str] = None
    scope: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    created_by: Optional[UUID] = None


class IpAllowlistResponse(BaseModel):
    id: UUID
    cidr: str
    scope: str
    description: Optional[str] = None
    is_active: bool
    created_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TotpBackupCodeCreate(BaseModel):
    user_id: UUID
    code_hash: str
    used: Optional[bool] = None
    used_at: Optional[datetime] = None


class TotpBackupCodeUpdate(BaseModel):
    user_id: Optional[UUID] = None
    code_hash: Optional[str] = None
    used: Optional[bool] = None
    used_at: Optional[datetime] = None


class TotpBackupCodeResponse(BaseModel):
    id: UUID
    user_id: UUID
    code_hash: str
    used: bool
    used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RateLimitEventCreate(BaseModel):
    ip_address: str
    user_id: Optional[UUID] = None
    endpoint: str


class RateLimitEventUpdate(BaseModel):
    ip_address: Optional[str] = None
    user_id: Optional[UUID] = None
    endpoint: Optional[str] = None


class RateLimitEventResponse(BaseModel):
    id: UUID
    ip_address: str
    user_id: Optional[UUID] = None
    endpoint: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Firing Profiles ---

class FiringProfileCreate(BaseModel):
    name: str
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

