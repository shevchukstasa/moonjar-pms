"""
Moonjar PMS — SQLAlchemy models (auto-generated from DATABASE_SCHEMA.sql)
"""

import uuid
from datetime import datetime, date, time

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import ARRAY as PgARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship

from api.database import Base
from api.enums import AuditActionType, BatchCreator, BatchMode, BatchStatus, BufferHealth, CastersRemovedReason, ChangeRequestStatus, DashboardType, DefectOutcome, DefectStage, ExpenseCategory, ExpenseType, GrindingStatus, IpScope, KilnConstantsMode, LanguagePreference, MaintenanceStatus, ManuShipmentStatus, MaterialType, MediaType, NotificationChannel, NotificationType, OrderSource, OrderStatus, PositionStatus, ProductType, PurchaseStatus, QcResult, QcStage, QmBlockType, ReconciliationStatus, ReferenceAction, RelatedEntityType, RepairStatus, ResourceStatus, ResourceType, ScheduleSlotStatus, ShapeType, SplitCategory, SurplusDispositionType, TaskStatus, TaskType, TpsDeviationType, TpsStatus, TransactionType, UserRole, WriteOffReason


def PgEnum(enum_class, **kwargs):
    """Enum helper: uses enum VALUES (lowercase) to match PostgreSQL DDL."""
    return sa.Enum(enum_class, values_callable=lambda x: [e.value for e in x], create_type=False, **kwargs)


class Factory(Base):
    __tablename__ = 'factories'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)
    location = Column(sa.String(200))
    address = Column(sa.Text)
    region = Column(sa.String(100))
    settings = Column(JSONB)
    timezone = Column(sa.String(50), nullable=False, default='Asia/Makassar')
    masters_group_chat_id = Column(sa.BigInteger)
    purchaser_chat_id = Column(sa.BigInteger)
    telegram_language = Column(sa.String(10), nullable=False, default='id')
    require_pm_approval_receiving = Column(sa.Boolean, nullable=False, default=False)
    kiln_constants_mode = Column(PgEnum(KilnConstantsMode), nullable=False, default=KilnConstantsMode.MANUAL)
    rotation_rules = Column(JSONB)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(sa.String(255), unique=True, nullable=False)
    name = Column(sa.String(200), nullable=False)
    role = Column(PgEnum(UserRole), nullable=False)
    password_hash = Column(sa.String(255))
    google_id = Column(sa.String(255), unique=True)
    telegram_user_id = Column(sa.BigInteger, unique=True)
    language = Column(PgEnum(LanguagePreference), nullable=False, default=LanguagePreference.EN)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    failed_login_count = Column(sa.Integer, nullable=False, default=0)
    locked_until = Column(sa.DateTime(timezone=True))
    totp_secret_encrypted = Column(sa.String(500))
    totp_enabled = Column(sa.Boolean, nullable=False, default=False)
    last_password_change = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class UserFactory(Base):
    __tablename__ = 'user_factories'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'factory_id'),
    )

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)
    contact_person = Column(sa.String(200))
    phone = Column(sa.String(50))
    email = Column(sa.String(255))
    address = Column(sa.Text)
    material_types = Column(sa.ARRAY(sa.String(50)))
    default_lead_time_days = Column(sa.Integer, nullable=False, default=35)
    rating = Column(sa.Numeric(3, 2))
    notes = Column(sa.Text)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class SupplierLeadTime(Base):
    __tablename__ = 'supplier_lead_times'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False)
    material_type = Column(sa.String(50), nullable=False)
    default_lead_time_days = Column(sa.Integer, nullable=False)
    avg_actual_lead_time_days = Column(sa.Numeric(5, 1))
    last_updated = Column(sa.DateTime(timezone=True))
    sample_count = Column(sa.Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('supplier_id', 'material_type'),
    )

    supplier = relationship('Supplier', foreign_keys=[supplier_id])


class Collection(Base):
    __tablename__ = 'collections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class Color(Base):
    __tablename__ = 'colors'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    code = Column(sa.String(20))
    is_basic = Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class ApplicationType(Base):
    __tablename__ = 'application_types'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class PlacesOfApplication(Base):
    __tablename__ = 'places_of_application'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(sa.String(50), unique=True, nullable=False)
    name = Column(sa.String(100), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class FinishingType(Base):
    __tablename__ = 'finishing_types'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class Size(Base):
    __tablename__ = 'sizes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(50), unique=True, nullable=False)
    width_mm = Column(sa.Integer, nullable=False)
    height_mm = Column(sa.Integer, nullable=False)
    is_custom = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class ReferenceAuditLog(Base):
    __tablename__ = 'reference_audit_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name = Column(sa.String(100), nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(PgEnum(ReferenceAction), nullable=False)
    old_values_json = Column(JSONB)
    new_values_json = Column(JSONB)
    changed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    changed_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    changed_by_rel = relationship('User', foreign_keys=[changed_by])


class ProductionOrder(Base):
    __tablename__ = 'production_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(sa.String(100), nullable=False)
    client = Column(sa.String(300), nullable=False)
    client_location = Column(sa.String(300))
    sales_manager_name = Column(sa.String(200))
    sales_manager_contact = Column(sa.String(300))
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    document_date = Column(sa.Date)
    production_received_date = Column(sa.Date)
    final_deadline = Column(sa.Date)
    schedule_deadline = Column(sa.Date)
    desired_delivery_date = Column(sa.Date)
    status = Column(PgEnum(OrderStatus), nullable=False, default=OrderStatus.NEW)
    status_override = Column(sa.Boolean, nullable=False, default=False)
    sales_status = Column(sa.String(100))
    source = Column(PgEnum(OrderSource), nullable=False, default=OrderSource.MANUAL)
    external_id = Column(sa.String(255))
    sales_payload_json = Column(JSONB)
    mandatory_qc = Column(sa.Boolean, nullable=False, default=False)
    notes = Column(sa.Text)
    shipped_at = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('source', 'external_id'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class ProductionOrderItem(Base):
    __tablename__ = 'production_order_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False)
    color = Column(sa.String(100), nullable=False)
    size = Column(sa.String(50), nullable=False)
    application = Column(sa.String(100))
    finishing = Column(sa.String(100))
    thickness = Column(sa.Numeric(5, 1), nullable=False, default=11.0)
    quantity_pcs = Column(sa.Integer, nullable=False)
    quantity_sqm = Column(sa.Numeric(10, 3))
    collection = Column(sa.String(100))
    application_type = Column(sa.String(100))
    place_of_application = Column(sa.String(50))
    product_type = Column(PgEnum(ProductType), nullable=False, default=ProductType.TILE)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', foreign_keys=[order_id])


class SalesWebhookEvent(Base):
    __tablename__ = 'sales_webhook_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(sa.String(255), unique=True, nullable=False)
    payload_json = Column(JSONB, nullable=False)
    processed = Column(sa.Boolean, nullable=False, default=False)
    error_message = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class ProductionOrderChangeRequest(Base):
    __tablename__ = 'production_order_change_requests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False)
    change_type = Column(sa.String(50), nullable=False, default='modification')
    diff_json = Column(JSONB, nullable=False)
    status = Column(PgEnum(ChangeRequestStatus), nullable=False, default=ChangeRequestStatus.PENDING)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    reviewed_at = Column(sa.DateTime(timezone=True))

    order = relationship('ProductionOrder', foreign_keys=[order_id])
    reviewed_by_rel = relationship('User', foreign_keys=[reviewed_by])


class ProductionOrderStatusLog(Base):
    __tablename__ = 'production_order_status_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False)
    old_status = Column(PgEnum(OrderStatus))
    new_status = Column(PgEnum(OrderStatus), nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    is_override = Column(sa.Boolean, nullable=False, default=False)
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', foreign_keys=[order_id])
    changed_by_rel = relationship('User', foreign_keys=[changed_by])


class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(300), nullable=False)
    collection = Column(sa.String(100))
    color = Column(sa.String(100))
    size = Column(sa.String(50))
    application_type = Column(sa.String(100))
    place_of_application = Column(sa.String(50))
    finishing_type = Column(sa.String(100))
    thickness_mm = Column(sa.Numeric(5, 1), nullable=False, default=11.0)
    description = Column(sa.Text)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('collection', 'color', 'size', 'application_type', 'place_of_application', 'finishing_type', 'thickness_mm'),
    )


class Material(Base):
    __tablename__ = 'materials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(300), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    balance = Column(sa.Numeric(12, 3), nullable=False, default=0)
    min_balance = Column(sa.Numeric(12, 3), nullable=False, default=0)
    min_balance_recommended = Column(sa.Numeric(12, 3))
    min_balance_auto = Column(sa.Boolean, nullable=False, default=True)
    avg_daily_consumption = Column(sa.Numeric(12, 3), default=0)
    unit = Column(sa.String(20), nullable=False, default='pcs')
    material_type = Column(sa.String(50), nullable=False)
    avg_monthly_consumption = Column(sa.Numeric(12, 3), default=0)
    warehouse_section = Column(sa.String(50), default='raw_materials')
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('name', 'factory_id'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    supplier = relationship('Supplier', foreign_keys=[supplier_id])


class RecipeMaterial(Base):
    __tablename__ = 'recipe_materials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    quantity_per_unit = Column(sa.Numeric(10, 4), nullable=False)
    unit = Column(sa.String(20), nullable=False, default='per_piece')
    notes = Column(sa.Text)

    __table_args__ = (
        UniqueConstraint('recipe_id', 'material_id'),
    )

    recipe = relationship('Recipe', foreign_keys=[recipe_id])
    material = relationship('Material', foreign_keys=[material_id])


class RecipeKilnConfig(Base):
    __tablename__ = 'recipe_kiln_config'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), unique=True, nullable=False)
    firing_temperature = Column(sa.Integer)
    firing_duration_hours = Column(sa.Numeric(5, 1))
    two_stage_firing = Column(sa.Boolean, nullable=False, default=False)
    special_instructions = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    recipe = relationship('Recipe', foreign_keys=[recipe_id])


class Resource(Base):
    __tablename__ = 'resources'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)
    resource_type = Column(PgEnum(ResourceType), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    capacity_sqm = Column(sa.Numeric(10, 3))
    capacity_pcs = Column(sa.Integer)
    num_levels = Column(sa.Integer, default=1)
    status = Column(PgEnum(ResourceStatus), nullable=False, default=ResourceStatus.ACTIVE)
    kiln_dimensions_cm = Column(JSONB)
    kiln_working_area_cm = Column(JSONB)
    kiln_multi_level = Column(sa.Boolean, default=False)
    kiln_coefficient = Column(sa.Numeric(4, 2))
    kiln_type = Column(sa.String(20))
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])


class Batch(Base):
    __tablename__ = 'batches'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    batch_date = Column(sa.Date, nullable=False)
    status = Column(PgEnum(BatchStatus), nullable=False, default=BatchStatus.PLANNED)
    created_by = Column(PgEnum(BatchCreator), nullable=False, default=BatchCreator.AUTO)
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    resource = relationship('Resource', foreign_keys=[resource_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class ScheduleSlot(Base):
    __tablename__ = 'schedule_slots'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    start_at = Column(sa.DateTime(timezone=True), nullable=False)
    end_at = Column(sa.DateTime(timezone=True), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'))
    status = Column(PgEnum(ScheduleSlotStatus), nullable=False, default=ScheduleSlotStatus.PLANNED)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    resource = relationship('Resource', foreign_keys=[resource_id])
    batch = relationship('Batch', foreign_keys=[batch_id])


class OrderPosition(Base):
    __tablename__ = 'order_positions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey('production_order_items.id'), nullable=False)
    parent_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    status = Column(PgEnum(PositionStatus), nullable=False, default=PositionStatus.PLANNED)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'))
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'))
    placement_position = Column(sa.String(100))
    placement_level = Column(sa.Integer)
    delay_hours = Column(sa.Numeric(8, 1), default=0)
    reservation_at = Column(sa.DateTime(timezone=True))
    materials_written_off_at = Column(sa.DateTime(timezone=True))
    quantity = Column(sa.Integer, nullable=False)
    quantity_sqm = Column(sa.Numeric(10, 3))
    quantity_with_defect_margin = Column(sa.Integer)
    color = Column(sa.String(100), nullable=False)
    size = Column(sa.String(50), nullable=False)
    application = Column(sa.String(100))
    finishing = Column(sa.String(100))
    collection = Column(sa.String(100))
    application_type = Column(sa.String(100))
    place_of_application = Column(sa.String(50))
    product_type = Column(PgEnum(ProductType), nullable=False, default=ProductType.TILE)
    shape = Column(PgEnum(ShapeType), default=ShapeType.RECTANGLE)
    thickness_mm = Column(sa.Numeric(5, 1), nullable=False, default=11.0)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'))
    mandatory_qc = Column(sa.Boolean, nullable=False, default=False)
    split_category = Column(PgEnum(SplitCategory))
    is_merged = Column(sa.Boolean, nullable=False, default=False)
    priority_order = Column(sa.Integer, default=0)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', foreign_keys=[order_id])
    order_item = relationship('ProductionOrderItem', foreign_keys=[order_item_id])
    parent_position = relationship('OrderPosition', remote_side=[id], foreign_keys=[parent_position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    batch = relationship('Batch', foreign_keys=[batch_id])
    resource = relationship('Resource', foreign_keys=[resource_id])
    recipe = relationship('Recipe', foreign_keys=[recipe_id])


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    type = Column(PgEnum(TaskType), nullable=False)
    status = Column(PgEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    assigned_role = Column(PgEnum(UserRole))
    related_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'))
    related_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    blocking = Column(sa.Boolean, nullable=False, default=False)
    description = Column(sa.Text)
    priority = Column(sa.Integer, nullable=False, default=0)
    due_at = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    completed_at = Column(sa.DateTime(timezone=True))
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    metadata_json = Column(JSONB)

    factory = relationship('Factory', foreign_keys=[factory_id])
    assigned_to_rel = relationship('User', foreign_keys=[assigned_to])
    related_order = relationship('ProductionOrder', foreign_keys=[related_order_id])
    related_position = relationship('OrderPosition', foreign_keys=[related_position_id])


class ProductionStage(Base):
    __tablename__ = 'production_stages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    order = Column(sa.Integer, unique=True, nullable=False)


class OrderStageHistory(Base):
    __tablename__ = 'order_stage_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='CASCADE'), nullable=False)
    stage_id = Column(UUID(as_uuid=True), ForeignKey('production_stages.id'), nullable=False)
    entered_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    exited_at = Column(sa.DateTime(timezone=True))

    order = relationship('ProductionOrder', foreign_keys=[order_id])
    stage = relationship('ProductionStage', foreign_keys=[stage_id])


class MaterialTransaction(Base):
    __tablename__ = 'material_transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    type = Column(PgEnum(TransactionType), nullable=False)
    quantity = Column(sa.Numeric(12, 3), nullable=False)
    related_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'))
    related_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    reason = Column(PgEnum(WriteOffReason))
    notes = Column(sa.Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    material = relationship('Material', foreign_keys=[material_id])
    related_order = relationship('ProductionOrder', foreign_keys=[related_order_id])
    related_position = relationship('OrderPosition', foreign_keys=[related_position_id])
    created_by_rel = relationship('User', foreign_keys=[created_by])


class MaterialPurchaseRequest(Base):
    __tablename__ = 'material_purchase_requests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    materials_json = Column(JSONB, nullable=False)
    status = Column(PgEnum(PurchaseStatus), nullable=False, default=PurchaseStatus.PENDING)
    source = Column(sa.String(20), nullable=False, default='auto')
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    sent_to_chat_at = Column(sa.DateTime(timezone=True))
    ordered_at = Column(sa.Date)
    expected_delivery_date = Column(sa.Date)
    actual_delivery_date = Column(sa.Date)
    received_quantity_json = Column(JSONB)
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    supplier = relationship('Supplier', foreign_keys=[supplier_id])
    approved_by_rel = relationship('User', foreign_keys=[approved_by])


class DefectCause(Base):
    __tablename__ = 'defect_causes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(sa.String(50), unique=True, nullable=False)
    category = Column(sa.String(100), nullable=False)
    description = Column(sa.Text)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class QualityCheck(Base):
    __tablename__ = 'quality_checks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    operation_type = Column(sa.String(100))
    stage = Column(PgEnum(QcStage), nullable=False)
    result = Column(PgEnum(QcResult), nullable=False)
    defect_cause_id = Column(UUID(as_uuid=True), ForeignKey('defect_causes.id'))
    photos = Column(sa.ARRAY(sa.Text))
    notes = Column(sa.Text)
    checked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    position = relationship('OrderPosition', foreign_keys=[position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    defect_cause = relationship('DefectCause', foreign_keys=[defect_cause_id])
    checked_by_rel = relationship('User', foreign_keys=[checked_by])


class QualityAssignmentConfig(Base):
    __tablename__ = 'quality_assignment_config'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    stage = Column(PgEnum(QcStage), nullable=False)
    base_percentage = Column(sa.Numeric(5, 2), nullable=False, default=2.0)
    increase_on_defect_percentage = Column(sa.Numeric(5, 2), nullable=False, default=2.0)
    current_percentage = Column(sa.Numeric(5, 2), nullable=False, default=2.0)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'stage'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class ProblemCard(Base):
    __tablename__ = 'problem_cards'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    location = Column(sa.String(200))
    description = Column(sa.Text, nullable=False)
    actions = Column(sa.Text)
    status = Column(sa.String(50), nullable=False, default='open')
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    created_by_rel = relationship('User', foreign_keys=[created_by])


class DefectRecord(Base):
    __tablename__ = 'defect_records'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    stage = Column(PgEnum(DefectStage), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    defect_type = Column(sa.String(200), nullable=False)
    quantity = Column(sa.Integer, nullable=False)
    outcome = Column(PgEnum(DefectOutcome), nullable=False)
    reported_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    reported_via = Column(sa.String(20), nullable=False, default='dashboard')
    photos = Column(sa.ARRAY(sa.Text))
    notes = Column(sa.Text)
    date = Column(sa.Date, nullable=False, server_default='CURRENT_DATE')
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    position = relationship('OrderPosition', foreign_keys=[position_id])
    batch = relationship('Batch', foreign_keys=[batch_id])
    supplier = relationship('Supplier', foreign_keys=[supplier_id])
    reported_by_rel = relationship('User', foreign_keys=[reported_by])


class StoneDefectCoefficient(Base):
    __tablename__ = 'stone_defect_coefficients'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    stone_type = Column(sa.String(100), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    coefficient = Column(sa.Numeric(4, 3), nullable=False, default=0.000)
    sample_size = Column(sa.Integer, nullable=False, default=0)
    last_updated = Column(sa.DateTime(timezone=True))
    calculation_period_days = Column(sa.Integer, nullable=False, default=30)

    __table_args__ = (
        UniqueConstraint('factory_id', 'stone_type', 'supplier_id'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    supplier = relationship('Supplier', foreign_keys=[supplier_id])


class GrindingStock(Base):
    __tablename__ = 'grinding_stock'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    color = Column(sa.String(100), nullable=False)
    size = Column(sa.String(50), nullable=False)
    quantity = Column(sa.Integer, nullable=False)
    source_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'))
    source_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    status = Column(PgEnum(GrindingStatus), nullable=False, default=GrindingStatus.IN_STOCK)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    source_order = relationship('ProductionOrder', foreign_keys=[source_order_id])
    source_position = relationship('OrderPosition', foreign_keys=[source_position_id])


class RepairQueue(Base):
    __tablename__ = 'repair_queue'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    color = Column(sa.String(100), nullable=False)
    size = Column(sa.String(50), nullable=False)
    quantity = Column(sa.Integer, nullable=False)
    defect_type = Column(sa.String(200))
    source_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'))
    source_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    status = Column(PgEnum(RepairStatus), nullable=False, default=RepairStatus.IN_REPAIR)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    repaired_at = Column(sa.DateTime(timezone=True))
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    source_order = relationship('ProductionOrder', foreign_keys=[source_order_id])
    source_position = relationship('OrderPosition', foreign_keys=[source_position_id])


class ManuShipment(Base):
    __tablename__ = 'manu_shipments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    items_json = Column(JSONB, nullable=False)
    status = Column(PgEnum(ManuShipmentStatus), nullable=False, default=ManuShipmentStatus.PENDING)
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    confirmed_at = Column(sa.DateTime(timezone=True))
    shipped_at = Column(sa.DateTime(timezone=True))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    confirmed_by_rel = relationship('User', foreign_keys=[confirmed_by])


class SurplusDisposition(Base):
    __tablename__ = 'surplus_dispositions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=False)
    surplus_quantity = Column(sa.Integer, nullable=False)
    disposition_type = Column(PgEnum(SurplusDispositionType), nullable=False)
    size = Column(sa.String(50), nullable=False)
    color = Column(sa.String(100), nullable=False)
    is_base_color = Column(sa.Boolean, nullable=False, default=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    order = relationship('ProductionOrder', foreign_keys=[order_id])
    position = relationship('OrderPosition', foreign_keys=[position_id])
    task = relationship('Task', foreign_keys=[task_id])


class CastersBox(Base):
    __tablename__ = 'casters_boxes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    color = Column(sa.String(100), nullable=False)
    size = Column(sa.String(50), nullable=False)
    quantity = Column(sa.Integer, nullable=False)
    source_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'))
    added_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    removed_at = Column(sa.DateTime(timezone=True))
    removed_reason = Column(PgEnum(CastersRemovedReason))
    notes = Column(sa.Text)

    factory = relationship('Factory', foreign_keys=[factory_id])
    source_order = relationship('ProductionOrder', foreign_keys=[source_order_id])


class OrderPackingPhoto(Base):
    __tablename__ = 'order_packing_photos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    photo_url = Column(sa.Text, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    uploaded_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    notes = Column(sa.Text)

    order = relationship('ProductionOrder', foreign_keys=[order_id])
    position = relationship('OrderPosition', foreign_keys=[position_id])
    uploaded_by_rel = relationship('User', foreign_keys=[uploaded_by])


class SupplierDefectReport(Base):
    __tablename__ = 'supplier_defect_reports'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    period_start = Column(sa.Date, nullable=False)
    period_end = Column(sa.Date, nullable=False)
    total_inspected = Column(sa.Integer, nullable=False, default=0)
    total_defective = Column(sa.Integer, nullable=False, default=0)
    defect_percentage = Column(sa.Numeric(5, 2), nullable=False, default=0)
    report_file_url = Column(sa.Text)
    sent_at = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    supplier = relationship('Supplier', foreign_keys=[supplier_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class StageReconciliationLog(Base):
    __tablename__ = 'stage_reconciliation_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'))
    stage_from = Column(sa.String(50), nullable=False)
    stage_to = Column(sa.String(50), nullable=False)
    input_count = Column(sa.Integer, nullable=False)
    output_good = Column(sa.Integer, nullable=False, default=0)
    output_defect = Column(sa.Integer, nullable=False, default=0)
    output_write_off = Column(sa.Integer, nullable=False, default=0)
    discrepancy = Column(sa.Integer, nullable=False, default=0)
    is_balanced = Column(sa.Boolean, nullable=False, default=True)
    checked_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    alert_sent = Column(sa.Boolean, nullable=False, default=False)

    factory = relationship('Factory', foreign_keys=[factory_id])
    batch = relationship('Batch', foreign_keys=[batch_id])


class Shift(Base):
    __tablename__ = 'shifts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    shift_number = Column(sa.Integer, nullable=False)
    shift_name = Column(sa.String(100))
    start_time = Column(sa.Time, nullable=False)
    end_time = Column(sa.Time, nullable=False)
    days_of_week = Column(sa.ARRAY(sa.Integer), default='{1,2,3,4,5,6}')
    is_active = Column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint('factory_id', 'shift_number'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class TpsParameter(Base):
    __tablename__ = 'tps_parameters'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    stage = Column(sa.String(100), nullable=False)
    metric_name = Column(sa.String(200), nullable=False)
    target_value = Column(sa.Numeric(12, 3), nullable=False)
    tolerance_percent = Column(sa.Numeric(5, 2), nullable=False, default=10.0)
    unit = Column(sa.String(50))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'stage', 'metric_name'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class TpsShiftMetric(Base):
    __tablename__ = 'tps_shift_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    shift = Column(sa.Integer, nullable=False)
    date = Column(sa.Date, nullable=False)
    stage = Column(sa.String(100), nullable=False)
    planned_output = Column(sa.Numeric(12, 3), nullable=False)
    actual_output = Column(sa.Numeric(12, 3), nullable=False)
    actual_output_pcs = Column(sa.Integer, nullable=False, default=0)
    deviation_percent = Column(sa.Numeric(8, 2), nullable=False, default=0)
    defect_rate = Column(sa.Numeric(5, 2), default=0)
    downtime_minutes = Column(sa.Numeric(8, 1), default=0)
    cycle_time_minutes = Column(sa.Numeric(8, 2), default=0)
    oee_percent = Column(sa.Numeric(5, 2), default=0)
    takt_time_minutes = Column(sa.Numeric(8, 2), default=0)
    status = Column(PgEnum(TpsStatus), nullable=False, default=TpsStatus.NORMAL)
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'shift', 'date', 'stage'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class TpsDeviation(Base):
    __tablename__ = 'tps_deviations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    shift = Column(sa.Integer, nullable=False)
    stage = Column(sa.String(100), nullable=False)
    deviation_type = Column(PgEnum(TpsDeviationType), nullable=False)
    description = Column(sa.Text, nullable=False)
    severity = Column(sa.String(20), nullable=False, default='low')
    resolved = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])


class ProcessStep(Base):
    __tablename__ = 'process_steps'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    norm_time_minutes = Column(sa.Numeric(8, 2), nullable=False)
    sequence = Column(sa.Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('factory_id', 'sequence'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class StandardWork(Base):
    __tablename__ = 'standard_work'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_step_id = Column(UUID(as_uuid=True), ForeignKey('process_steps.id', ondelete='CASCADE'), nullable=False)
    description = Column(sa.Text, nullable=False)
    time_minutes = Column(sa.Numeric(8, 2), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    process_step = relationship('ProcessStep', foreign_keys=[process_step_id])


class BottleneckConfig(Base):
    __tablename__ = 'bottleneck_config'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), unique=True, nullable=False)
    constraint_resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'))
    buffer_target_hours = Column(sa.Numeric(6, 1), nullable=False, default=24.0)
    rope_limit = Column(sa.Integer)
    rope_max_days = Column(sa.Integer, nullable=False, default=2)
    rope_min_days = Column(sa.Integer, nullable=False, default=1)
    batch_mode = Column(PgEnum(BatchMode), nullable=False, default=BatchMode.HYBRID)
    current_bottleneck_utilization = Column(sa.Numeric(5, 2), default=0)

    factory = relationship('Factory', foreign_keys=[factory_id])
    constraint_resource = relationship('Resource', foreign_keys=[constraint_resource_id])


class BufferStatus(Base):
    __tablename__ = 'buffer_status'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    buffered_positions_count = Column(sa.Integer, nullable=False, default=0)
    buffered_sqm = Column(sa.Numeric(10, 3), nullable=False, default=0)
    buffer_health = Column(PgEnum(BufferHealth), nullable=False, default=BufferHealth.GREEN)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    resource = relationship('Resource', foreign_keys=[resource_id])


class KilnMaintenanceSchedule(Base):
    __tablename__ = 'kiln_maintenance_schedule'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    maintenance_type = Column(sa.String(200), nullable=False)
    scheduled_date = Column(sa.Date, nullable=False)
    status = Column(PgEnum(MaintenanceStatus), nullable=False, default=MaintenanceStatus.PLANNED)
    notes = Column(sa.Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    resource = relationship('Resource', foreign_keys=[resource_id])
    created_by_rel = relationship('User', foreign_keys=[created_by])


class KilnMaintenanceMaterial(Base):
    __tablename__ = 'kiln_maintenance_materials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    maintenance_id = Column(UUID(as_uuid=True), ForeignKey('kiln_maintenance_schedule.id', ondelete='CASCADE'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    required_quantity = Column(sa.Numeric(12, 3), nullable=False)
    in_stock_quantity = Column(sa.Numeric(12, 3), nullable=False, default=0)

    maintenance = relationship('KilnMaintenanceSchedule', foreign_keys=[maintenance_id])
    material = relationship('Material', foreign_keys=[material_id])


class KilnConstant(Base):
    __tablename__ = 'kiln_constants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constant_name = Column(sa.String(100), unique=True, nullable=False)
    value = Column(sa.Numeric(12, 4), nullable=False)
    unit = Column(sa.String(50))
    description = Column(sa.Text)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    updated_by_rel = relationship('User', foreign_keys=[updated_by])


class DailyTaskDistribution(Base):
    __tablename__ = 'daily_task_distributions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    distribution_date = Column(sa.Date, nullable=False)
    glazing_tasks_json = Column(JSONB)
    kiln_loading_json = Column(JSONB)
    glaze_recipes_json = Column(JSONB)
    sent_at = Column(sa.DateTime(timezone=True))
    sent_to_chat = Column(sa.Boolean, nullable=False, default=False)
    message_id = Column(sa.BigInteger)

    __table_args__ = (
        UniqueConstraint('factory_id', 'distribution_date'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'))
    type = Column(PgEnum(NotificationType), nullable=False)
    title = Column(sa.String(500), nullable=False)
    message = Column(sa.Text)
    related_entity_type = Column(PgEnum(RelatedEntityType))
    related_entity_id = Column(UUID(as_uuid=True))
    is_read = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class AiChatHistory(Base):
    __tablename__ = 'ai_chat_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    messages_json = Column(JSONB, nullable=False, default='[]')
    context = Column(sa.Text)
    session_name = Column(sa.String(200))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])


class KilnCalculationLog(Base):
    __tablename__ = 'kiln_calculation_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calculation_type = Column(sa.String(100), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'))
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'))
    input_json = Column(JSONB, nullable=False)
    output_json = Column(JSONB, nullable=False)
    duration_ms = Column(sa.Integer)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    batch = relationship('Batch', foreign_keys=[batch_id])
    resource = relationship('Resource', foreign_keys=[resource_id])


class WorkerMedia(Base):
    __tablename__ = 'worker_media'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(sa.String(255))
    file_url = Column(sa.Text)
    media_type = Column(PgEnum(MediaType), nullable=False)
    telegram_user_id = Column(sa.BigInteger)
    related_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'))
    related_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    related_order = relationship('ProductionOrder', foreign_keys=[related_order_id])
    related_position = relationship('OrderPosition', foreign_keys=[related_position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class RagEmbedding(Base):
    __tablename__ = 'rag_embeddings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_table = Column(sa.String(100), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    content_text = Column(sa.Text, nullable=False)
    content_tsvector = Column(TSVECTOR)                  # full-text search index
    embedding = Column(PgARRAY(sa.Float))                # float[] — no pgvector needed
    metadata_json = Column(JSONB)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class UserDashboardAccess(Base):
    __tablename__ = 'user_dashboard_access'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    dashboard_type = Column(PgEnum(DashboardType), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    granted_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'dashboard_type'),
    )

    user = relationship('User', foreign_keys=[user_id])
    granted_by_rel = relationship('User', foreign_keys=[granted_by])


class NotificationPreference(Base):
    __tablename__ = 'notification_preferences'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category = Column(sa.String(50), nullable=False)
    channel = Column(PgEnum(NotificationChannel), nullable=False, default=NotificationChannel.IN_APP)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'category'),
    )

    user = relationship('User', foreign_keys=[user_id])


class FinancialEntry(Base):
    __tablename__ = 'financial_entries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    entry_type = Column(PgEnum(ExpenseType), nullable=False)
    category = Column(PgEnum(ExpenseCategory), nullable=False)
    amount = Column(sa.Numeric(14, 2), nullable=False)
    currency = Column(sa.String(3), nullable=False, default='USD')
    description = Column(sa.Text)
    entry_date = Column(sa.Date, nullable=False)
    reference_id = Column(UUID(as_uuid=True))
    reference_type = Column(sa.String(50))
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    created_by_rel = relationship('User', foreign_keys=[created_by])


class OrderFinancial(Base):
    __tablename__ = 'order_financials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'), unique=True, nullable=False)
    total_price = Column(sa.Numeric(14, 2))
    currency = Column(sa.String(3), nullable=False, default='USD')
    cost_estimate = Column(sa.Numeric(14, 2))
    margin_percent = Column(sa.Numeric(5, 2))
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', foreign_keys=[order_id])


class WarehouseSection(Base):
    __tablename__ = 'warehouse_sections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    code = Column(sa.String(50), nullable=False)
    name = Column(sa.String(200), nullable=False)
    is_default = Column(sa.Boolean, nullable=False, default=False)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'code'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])


class InventoryReconciliation(Base):
    __tablename__ = 'inventory_reconciliations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey('warehouse_sections.id'))
    status = Column(PgEnum(ReconciliationStatus), nullable=False, default=ReconciliationStatus.IN_PROGRESS)
    started_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    completed_at = Column(sa.DateTime(timezone=True))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    section = relationship('WarehouseSection', foreign_keys=[section_id])
    started_by_rel = relationship('User', foreign_keys=[started_by])


class InventoryReconciliationItem(Base):
    __tablename__ = 'inventory_reconciliation_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(UUID(as_uuid=True), ForeignKey('inventory_reconciliations.id', ondelete='CASCADE'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    system_quantity = Column(sa.Numeric(12, 3), nullable=False)
    actual_quantity = Column(sa.Numeric(12, 3), nullable=False)
    difference = Column(sa.Numeric(12, 3), nullable=False)
    adjustment_applied = Column(sa.Boolean, nullable=False, default=False)

    reconciliation = relationship('InventoryReconciliation', foreign_keys=[reconciliation_id])
    material = relationship('Material', foreign_keys=[material_id])


class QmBlock(Base):
    __tablename__ = 'qm_blocks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    block_type = Column(PgEnum(QmBlockType), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'))
    reason = Column(sa.Text, nullable=False)
    severity = Column(sa.String(20), nullable=False, default='critical')
    photo_urls = Column(JSONB, default='[]')
    blocked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    resolved_at = Column(sa.DateTime(timezone=True))
    resolution_note = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    position = relationship('OrderPosition', foreign_keys=[position_id])
    batch = relationship('Batch', foreign_keys=[batch_id])
    blocked_by_rel = relationship('User', foreign_keys=[blocked_by])
    resolved_by_rel = relationship('User', foreign_keys=[resolved_by])


class KilnLoadingRule(Base):
    __tablename__ = 'kiln_loading_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kiln_id = Column(UUID(as_uuid=True), ForeignKey('resources.id', ondelete='CASCADE'), nullable=False)
    rules = Column(JSONB, nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('kiln_id'),
    )

    kiln = relationship('Resource', foreign_keys=[kiln_id])


class KilnFiringSchedule(Base):
    __tablename__ = 'kiln_firing_schedules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kiln_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    name = Column(sa.String(200), nullable=False)
    schedule_data = Column(JSONB, nullable=False)
    is_default = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    kiln = relationship('Resource', foreign_keys=[kiln_id])


class KilnActualLoad(Base):
    __tablename__ = 'kiln_actual_loads'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kiln_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id'), nullable=False)
    actual_pieces = Column(sa.Integer, nullable=False)
    actual_area_sqm = Column(sa.Numeric(10, 3))
    calculated_capacity = Column(sa.Integer, nullable=False)
    loading_type = Column(sa.String(20), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    kiln = relationship('Resource', foreign_keys=[kiln_id])
    batch = relationship('Batch', foreign_keys=[batch_id])


class SecurityAuditLog(Base):
    __tablename__ = 'security_audit_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(PgEnum(AuditActionType), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    actor_email = Column(sa.String(255))
    ip_address = Column(INET, nullable=False)
    user_agent = Column(sa.Text)
    target_entity = Column(sa.String(100))
    target_id = Column(UUID(as_uuid=True))
    details = Column(JSONB)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    actor = relationship('User', foreign_keys=[actor_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class ActiveSession(Base):
    __tablename__ = 'active_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_jti = Column(sa.String(64), unique=True, nullable=False)
    ip_address = Column(INET, nullable=False)
    user_agent = Column(sa.Text)
    device_label = Column(sa.String(200))
    expires_at = Column(sa.DateTime(timezone=True), nullable=False)
    revoked = Column(sa.Boolean, nullable=False, default=False)
    revoked_at = Column(sa.DateTime(timezone=True))
    revoked_reason = Column(sa.String(100))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])


class IpAllowlist(Base):
    __tablename__ = 'ip_allowlist'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cidr = Column(INET, nullable=False)
    scope = Column(PgEnum(IpScope), nullable=False)
    description = Column(sa.String(200))
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    created_by_rel = relationship('User', foreign_keys=[created_by])


class TotpBackupCode(Base):
    __tablename__ = 'totp_backup_codes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    code_hash = Column(sa.String(255), nullable=False)
    used = Column(sa.Boolean, nullable=False, default=False)
    used_at = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])


class RateLimitEvent(Base):
    __tablename__ = 'rate_limit_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address = Column(INET, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    endpoint = Column(sa.String(200), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])


class FinishedGoodsStock(Base):
    __tablename__ = 'finished_goods_stock'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    color = Column(sa.String(100), nullable=False)
    size = Column(sa.String(50), nullable=False)
    collection = Column(sa.String(100))
    product_type = Column(PgEnum(ProductType), default=ProductType.TILE)
    quantity = Column(sa.Integer, nullable=False, default=0)
    reserved_quantity = Column(sa.Integer, nullable=False, default=0)
    updated_at = Column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'color', 'size', 'collection', 'product_type',
                         name='uq_finished_goods_stock'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])

