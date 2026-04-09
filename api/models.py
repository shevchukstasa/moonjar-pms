"""
Moonjar PMS — SQLAlchemy models (auto-generated from DATABASE_SCHEMA.sql)
"""

import uuid
from datetime import datetime, date, time, timezone

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import ARRAY as PgARRAY
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship

from api.database import Base
# noqa: dead-code — all enums needed for PgEnum declarations
from api.enums import AuditActionType, BackupStatus, BackupType, BatchCreator, BatchMode, BatchStatus, BufferHealth, CastersRemovedReason, ChangeRequestStatus, DashboardType, DefectOutcome, DefectStage, EngobeType, ExpenseCategory, ExpenseType, GrindingStatus, IpScope, KilnConstantsMode, LanguagePreference, MaintenanceStatus, ManaShipmentStatus, MaterialType, MediaType, NotificationChannel, NotificationType, OrderSource, OrderStatus, PositionStatus, ProblemCardMode, ProductType, PurchaseStatus, QcResult, QcStage, QmBlockType, ReconciliationStatus, ReferenceAction, RelatedEntityType, RepairStatus, ResourceStatus, ResourceType, ScheduleSlotStatus, ShapeType, SplitCategory, SurplusDispositionType, TaskStatus, TaskType, TpsDeviationType, TpsStatus, TransactionType, UserRole, WriteOffReason


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
    receiving_approval_mode = Column(sa.String(20), nullable=False, server_default='all')  # 'all' or 'auto'
    kiln_constants_mode = Column(PgEnum(KilnConstantsMode), nullable=False, default=KilnConstantsMode.MANUAL)
    rotation_rules = Column(JSONB)
    served_locations = Column(JSONB)  # ["Bali", "Lombok"] — delivery locations served by this factory
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

    # Reverse relationship for factory scoping (apply_factory_filter)
    user_factories = relationship('UserFactory', foreign_keys='UserFactory.user_id', back_populates='user', lazy='selectin')


class UserFactory(Base):
    __tablename__ = 'user_factories'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'factory_id'),
    )

    user = relationship('User', foreign_keys=[user_id], back_populates='user_factories')
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


class SupplierSubgroup(Base):
    """Many-to-many: supplier ↔ material subgroups."""
    __tablename__ = 'supplier_subgroups'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False)
    subgroup_id = Column(UUID(as_uuid=True), ForeignKey('material_subgroups.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('supplier_id', 'subgroup_id'),
    )

    supplier = relationship('Supplier', foreign_keys=[supplier_id])
    subgroup = relationship('MaterialSubgroup', foreign_keys=[subgroup_id])


class SupplierLeadTime(Base):
    __tablename__ = 'supplier_lead_times'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False)
    material_type = Column(sa.String(50), nullable=False)
    default_lead_time_days = Column(sa.Integer, nullable=False)
    avg_actual_lead_time_days = Column(sa.Numeric(8, 2))
    last_updated = Column(sa.DateTime(timezone=True))
    sample_count = Column(sa.Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint('supplier_id', 'material_type'),
    )

    supplier = relationship('Supplier', foreign_keys=[supplier_id])


class Collection(Base):
    """Product collections (for finished tiles/products)."""
    __tablename__ = 'collections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class ColorCollection(Base):
    """Color collections (for glaze recipes). Separate from product Collections."""
    __tablename__ = 'color_collections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), unique=True, nullable=False)
    description = Column(sa.String(255))
    is_active = Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
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
    thickness_mm = Column(sa.Integer, nullable=True)
    shape = Column(sa.String(20), nullable=True, default='rectangle')
    is_custom = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    glazing_board_spec = relationship('GlazingBoardSpec', back_populates='size', uselist=False)


class GlazingBoardSpec(Base):
    """Glazing board spec for each tile size.

    Stores how many tiles fit on one glazing board and whether a custom
    board width is required. Masters measure glaze consumption per two boards,
    so each board should hold ~0.22–0.23 m² of tile area.
    """
    __tablename__ = 'glazing_board_specs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    size_id = Column(UUID(as_uuid=True), ForeignKey('sizes.id'), nullable=False, unique=True)
    board_length_cm = Column(sa.Numeric(6, 1), nullable=False, default=122.0)
    board_width_cm = Column(sa.Numeric(6, 1), nullable=False)
    tiles_per_board = Column(sa.Integer, nullable=False)
    area_per_board_m2 = Column(sa.Numeric(8, 4), nullable=False)
    area_per_two_boards_m2 = Column(sa.Numeric(8, 4))  # 2× area — workers glaze 2 boards at a time
    tiles_along_length = Column(sa.Integer, nullable=False)
    tiles_across_width = Column(sa.Integer, nullable=False)
    tile_orientation_cm = Column(sa.String(30))  # e.g. "10×30"
    is_custom_board = Column(sa.Boolean, nullable=False, default=False)
    notes = Column(sa.Text)
    calculated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    size = relationship('Size', back_populates='glazing_board_spec')


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
    # Cancellation request fields (set by Sales App via integration endpoint)
    cancellation_requested = Column(sa.Boolean, nullable=False, default=False)
    cancellation_requested_at = Column(sa.DateTime(timezone=True), nullable=True)
    # "pending" | "accepted" | "rejected" | None
    cancellation_decision = Column(sa.String(20), nullable=True)
    cancellation_decided_at = Column(sa.DateTime(timezone=True), nullable=True)
    cancellation_decided_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    # Change request fields (set by Sales App via webhook when order already exists)
    change_req_payload = Column(JSONB, nullable=True)
    change_req_status = Column(sa.String(20), nullable=False, server_default='none')
    change_req_requested_at = Column(sa.DateTime(timezone=True), nullable=True)
    change_req_decided_at = Column(sa.DateTime(timezone=True), nullable=True)
    change_req_decided_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
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
    color_2 = Column(sa.String(100))              # Second color for Stencil/Silkscreen/Custom
    size = Column(sa.String(50), nullable=False)
    application = Column(sa.String(100))
    finishing = Column(sa.String(100))
    thickness = Column(sa.Numeric(8, 2), nullable=False, default=11.0)
    quantity_pcs = Column(sa.Integer, nullable=False)
    quantity_sqm = Column(sa.Numeric(10, 3))
    collection = Column(sa.String(100))
    application_type = Column(sa.String(100))
    place_of_application = Column(sa.String(50))
    product_type = Column(PgEnum(ProductType), nullable=False, default=ProductType.TILE)
    # Shape & dimension data (from Sales app or manual form)
    shape = Column(sa.String(20))        # rectangle, round, triangle, octagon, freeform
    length_cm = Column(sa.Numeric(7, 2))
    width_cm = Column(sa.Numeric(7, 2))
    depth_cm = Column(sa.Numeric(7, 2))  # sinks only
    bowl_shape = Column(sa.String(20))   # sinks only: parallelepiped, half_oval, other
    shape_dimensions = Column(sa.JSON, nullable=True)  # Shape-specific measurements (JSONB)
    # Edge profile data (from Sales app)
    edge_profile = Column(sa.String(30), nullable=True)           # enum value: 'straight', 'bullnose', etc.
    edge_profile_sides = Column(sa.SmallInteger, nullable=True)   # 1, 2, 3, 4 — number of profiled sides
    edge_profile_notes = Column(sa.String(255), nullable=True)    # description for custom profile
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', foreign_keys=[order_id])


class SalesWebhookEvent(Base):
    __tablename__ = 'sales_webhook_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(sa.String(255), unique=True, nullable=False)
    payload_json = Column(JSONB, nullable=False)
    processed = Column(sa.Boolean, nullable=False, default=False)
    error_message = Column(sa.Text)
    retry_count = Column(sa.Integer, nullable=False, default=0, server_default=sa.text("0"))
    permanently_failed = Column(sa.Boolean, nullable=False, default=False, server_default=sa.text("false"))
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
    color_collection = Column(sa.String(100))
    # Color collection (e.g. "Collection 2025/2026") — renamed from 'collection'
    description = Column(sa.Text)
    recipe_type = Column(sa.String(20), nullable=False, default='product')
    # values: 'product', 'glaze', 'engobe'
    color_type = Column(sa.String(20))
    # values: 'base', 'custom', None
    specific_gravity = Column(sa.Numeric(8, 4))
    # SG (удельный вес) — for converting dry grams → ml of liquid glaze
    consumption_spray_ml_per_sqm = Column(sa.Numeric(8, 2))
    # Spray application consumption rate in ml per m²
    consumption_brush_ml_per_sqm = Column(sa.Numeric(8, 2))
    # Brush application consumption rate in ml per m²
    engobe_type = Column(PgEnum(EngobeType), nullable=True)
    # Only set when recipe_type='engobe': 'standard', 'shelf_coating', 'hole_filler'
    is_default = Column(sa.Boolean, nullable=False, default=False)
    # Default recipe flag — system auto-picks this recipe for given recipe_type (e.g. engobe)
    client_name = Column(sa.String(200))
    # Client name — for color matching recipes linked to a specific client
    glaze_settings = Column(JSONB, nullable=False, default=dict)
    # Legacy per-recipe glaze config (consumption_ml_per_sqm migrated to dedicated columns)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('color_collection', 'name',
                         name='uq_recipes_colcollection_name'),
    )


class MaterialGroup(Base):
    """Top-level material category — e.g. 'Tile materials', 'Finished products', 'Equipment'."""
    __tablename__ = 'material_groups'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False, unique=True)
    code = Column(sa.String(50), nullable=False, unique=True)
    description = Column(sa.Text)
    icon = Column(sa.String(10))
    display_order = Column(sa.Integer, nullable=False, default=0)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    subgroups = relationship('MaterialSubgroup', back_populates='group', cascade='all, delete-orphan',
                             order_by='MaterialSubgroup.display_order')


class MaterialSubgroup(Base):
    """Second-level material category — e.g. 'Stone', 'Pigment' within 'Tile materials'."""
    __tablename__ = 'material_subgroups'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey('material_groups.id', ondelete='CASCADE'), nullable=False)
    name = Column(sa.String(200), nullable=False)
    code = Column(sa.String(50), nullable=False, unique=True)
    description = Column(sa.Text)
    icon = Column(sa.String(10))
    default_lead_time_days = Column(sa.Integer)
    default_unit = Column(sa.String(20), default='kg')
    display_order = Column(sa.Integer, nullable=False, default=0)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('group_id', 'name', name='uq_subgroup_group_name'),
    )

    group = relationship('MaterialGroup', back_populates='subgroups')
    materials = relationship('Material', back_populates='subgroup')


class Material(Base):
    """Shared material catalog — name, type, unit, supplier (no factory scope)."""
    __tablename__ = 'materials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_code = Column(sa.String(20), unique=True)  # auto-generated, e.g. "M-0001"
    name = Column(sa.String(300), unique=True, nullable=False)
    unit = Column(sa.String(20), nullable=False, default='pcs')
    material_type = Column(sa.String(50), nullable=False)
    product_subtype = Column(sa.String(30), nullable=True)  # tiles/sinks/table_top/custom — for stone & ready stock
    subgroup_id = Column(UUID(as_uuid=True), ForeignKey('material_subgroups.id'))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id'))
    size_id = Column(UUID(as_uuid=True), ForeignKey('sizes.id'), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    supplier = relationship('Supplier', foreign_keys=[supplier_id])
    subgroup = relationship('MaterialSubgroup', back_populates='materials')
    size = relationship('Size', foreign_keys=[size_id])
    stocks = relationship('MaterialStock', back_populates='material', cascade='all, delete-orphan')


class MaterialStock(Base):
    """Per-factory material stock — balance, thresholds, consumption metrics."""
    __tablename__ = 'material_stock'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    balance = Column(sa.Numeric(12, 3), nullable=False, default=0)
    min_balance = Column(sa.Numeric(12, 3), nullable=False, default=0)
    min_balance_recommended = Column(sa.Numeric(12, 3))
    min_balance_auto = Column(sa.Boolean, nullable=False, default=True)
    avg_daily_consumption = Column(sa.Numeric(12, 3), default=0)
    avg_monthly_consumption = Column(sa.Numeric(12, 3), default=0)
    warehouse_section = Column(sa.String(50), default='raw_materials')
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('material_id', 'factory_id'),
    )

    material = relationship('Material', foreign_keys=[material_id], back_populates='stocks')
    factory = relationship('Factory', foreign_keys=[factory_id])


class RecipeMaterial(Base):
    __tablename__ = 'recipe_materials'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    quantity_per_unit = Column(sa.Numeric(10, 4), nullable=False)
    unit = Column(sa.String(20), nullable=False, default='per_piece')
    notes = Column(sa.Text)
    # Per-method consumption rates (ml/m²)
    spray_rate = Column(sa.Numeric(10, 4), nullable=True)
    brush_rate = Column(sa.Numeric(10, 4), nullable=True)
    splash_rate = Column(sa.Numeric(10, 4), nullable=True)
    silk_screen_rate = Column(sa.Numeric(10, 4), nullable=True)

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
    firing_duration_hours = Column(sa.Numeric(8, 2))
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
    # Equipment installed on this kiln
    thermocouple = Column(sa.String(50))       # "chinese" | "indonesia_manufacture"
    control_cable = Column(sa.String(50))      # "indonesia_manufacture"
    control_device = Column(sa.String(50))     # "oven" | "moonjar"
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    equipment_configs = relationship(
        'KilnEquipmentConfig',
        back_populates='kiln',
        cascade='all, delete-orphan',
        order_by='desc(KilnEquipmentConfig.effective_from)',
    )


class KilnEquipmentConfig(Base):
    """History of equipment installed on a kiln.

    Each row is a snapshot of what thermocouple / controller / cable /
    typology was physically on the kiln during a time window. Exactly
    one row per kiln has effective_to=NULL (the "current" config).

    Downstream layers — temperature set-points, firing profiles, recipe
    capability — reference a specific config id. When equipment is
    swapped, the current row is closed (effective_to=now) and a fresh
    one is created; all dependent records are flagged for requalification.
    """
    __tablename__ = 'kiln_equipment_configs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kiln_id = Column(
        UUID(as_uuid=True),
        ForeignKey('resources.id', ondelete='CASCADE'),
        nullable=False,
    )

    typology = Column(sa.String(30))  # horizontal | vertical | raku

    thermocouple_brand = Column(sa.String(100))
    thermocouple_model = Column(sa.String(100))
    thermocouple_length_cm = Column(sa.Integer)
    thermocouple_position = Column(sa.String(100))

    controller_brand = Column(sa.String(100))
    controller_model = Column(sa.String(100))

    cable_brand = Column(sa.String(100))
    cable_length_cm = Column(sa.Integer)
    cable_type = Column(sa.String(100))

    notes = Column(sa.Text)
    extras = Column(JSONB)

    effective_from = Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    effective_to = Column(sa.DateTime(timezone=True))

    installed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    reason = Column(sa.String(200))

    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    kiln = relationship('Resource', back_populates='equipment_configs')


class KilnTemperatureSetpoint(Base):
    """Layer 2: actual controller set-point for a temperature group on a
    specific kiln equipment configuration.

    The abstract target (group.temperature) is what we want on the tile;
    setpoint_c is what we dial into the controller to achieve it, given
    the thermocouple/controller/cable combination installed on the kiln.
    """
    __tablename__ = 'kiln_temperature_setpoints'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temperature_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('firing_temperature_groups.id', ondelete='CASCADE'),
        nullable=False,
    )
    kiln_equipment_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey('kiln_equipment_configs.id', ondelete='CASCADE'),
        nullable=False,
    )
    setpoint_c = Column(sa.Integer, nullable=False)
    notes = Column(sa.Text)
    calibrated_at = Column(sa.DateTime(timezone=True))
    calibrated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    needs_recalibration = Column(sa.Boolean, nullable=False, default=False)

    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    temperature_group = relationship('FiringTemperatureGroup')
    equipment_config = relationship('KilnEquipmentConfig')

    __table_args__ = (
        UniqueConstraint(
            'temperature_group_id', 'kiln_equipment_config_id',
            name='uq_setpoint_group_config',
        ),
    )


class Batch(Base):
    __tablename__ = 'batches'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    batch_date = Column(sa.Date, nullable=False)
    status = Column(PgEnum(BatchStatus), nullable=False, default=BatchStatus.PLANNED)
    created_by = Column(PgEnum(BatchCreator), nullable=False, default=BatchCreator.AUTO)
    notes = Column(sa.Text)
    metadata_json = Column(JSONB)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    firing_profile_id = Column(UUID(as_uuid=True), ForeignKey('firing_profiles.id'))
    target_temperature = Column(sa.Integer)

    resource = relationship('Resource', foreign_keys=[resource_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    firing_profile = relationship('FiringProfile', foreign_keys=[firing_profile_id])


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
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id', ondelete='SET NULL'))
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id', ondelete='SET NULL'))
    placement_position = Column(sa.String(100))
    placement_level = Column(sa.Integer)
    delay_hours = Column(sa.Numeric(8, 1), default=0)
    reservation_at = Column(sa.DateTime(timezone=True))
    materials_written_off_at = Column(sa.DateTime(timezone=True))
    quantity = Column(sa.Integer, nullable=False)
    quantity_sqm = Column(sa.Numeric(10, 3))
    quantity_with_defect_margin = Column(sa.Integer)
    color = Column(sa.String(100), nullable=False)
    color_2 = Column(sa.String(100))              # Second color for Stencil/Silkscreen/Custom
    size = Column(sa.String(50), nullable=False)
    application = Column(sa.String(100))
    finishing = Column(sa.String(100))
    collection = Column(sa.String(100))
    application_type = Column(sa.String(100))
    place_of_application = Column(sa.String(50))
    product_type = Column(PgEnum(ProductType), nullable=False, default=ProductType.TILE)
    shape = Column(PgEnum(ShapeType), default=ShapeType.RECTANGLE)
    # Shape dimensions for surface area calculation
    length_cm = Column(sa.Numeric(7, 2))             # Length in cm (from Sales/kiln calculator)
    width_cm = Column(sa.Numeric(7, 2))              # Width in cm
    depth_cm = Column(sa.Numeric(7, 2))              # Depth in cm (sinks only)
    bowl_shape = Column(sa.String(20))               # Bowl shape: parallelepiped/half_oval/other (sinks)
    shape_dimensions = Column(sa.JSON, nullable=True)  # Shape-specific measurements (JSONB), e.g.:
    # triangle: {"side_a_cm": 10, "side_b_cm": 10, "side_c_cm": 14.14}
    # octagon: {"width_cm": 15, "height_cm": 15, "cut_cm": 2.5}
    # circle: {"diameter_cm": 20}
    # freeform: {"manual_area_cm2": 150.5}
    # Edge profile data
    edge_profile = Column(sa.String(30), nullable=True)           # enum value: 'straight', 'bullnose', etc.
    edge_profile_sides = Column(sa.SmallInteger, nullable=True)   # 1, 2, 3, 4 — number of profiled sides
    edge_profile_notes = Column(sa.String(255), nullable=True)    # description for custom profile
    glazeable_sqm = Column(sa.Numeric(10, 4))        # Glazeable surface area per piece (m²)
    thickness_mm = Column(sa.Numeric(8, 2), nullable=False, default=11.0)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='SET NULL'))
    size_id = Column(UUID(as_uuid=True), ForeignKey('sizes.id'), nullable=True)
    mandatory_qc = Column(sa.Boolean, nullable=False, default=False)
    split_category = Column(PgEnum(SplitCategory))
    is_merged = Column(sa.Boolean, nullable=False, default=False)
    priority_order = Column(sa.Integer, default=0)
    firing_round = Column(sa.Integer, nullable=False, default=1)
    two_stage_firing = Column(sa.Boolean, nullable=False, default=False, server_default='false')
    two_stage_type = Column(sa.String(20), nullable=True)  # 'gold' or 'countertop' or null
    application_collection_code = Column(sa.String(30), nullable=True)  # 'exclusive', 'authentic', etc.
    application_method_code = Column(sa.String(20), nullable=True)      # 'ss', 'bs', 'sb', etc.
    # ── Upfront schedule (TOC/DBR backward scheduling) ──────────────────
    planned_glazing_date = Column(sa.Date)          # when glazing should start
    planned_kiln_date = Column(sa.Date)             # when kiln firing should happen
    planned_sorting_date = Column(sa.Date)          # when sorting should happen
    planned_completion_date = Column(sa.Date)       # when position should be complete
    estimated_kiln_id = Column(UUID(as_uuid=True), ForeignKey('resources.id', ondelete='SET NULL'))
    estimated_num_loads = Column(sa.Integer, nullable=True)  # how many kiln firings this position needs
    schedule_metadata = Column(JSONB)                        # scheduler/batch planner metadata (original dates, deferrals)
    schedule_version = Column(sa.Integer, nullable=False, default=1)
    # Human-readable position numbering within the order:
    #   position_number — sequential integer for root positions (1, 2, 3, …)
    #   split_index     — NULL for roots; 1, 2, 3 for split sub-positions
    # Display: root → "#3", sub → "#3.1"
    position_number = Column(sa.Integer, nullable=True)
    split_index = Column(sa.Integer, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', foreign_keys=[order_id])
    order_item = relationship('ProductionOrderItem', foreign_keys=[order_item_id])
    parent_position = relationship('OrderPosition', remote_side=[id], foreign_keys=[parent_position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    batch = relationship('Batch', foreign_keys=[batch_id])
    resource = relationship('Resource', foreign_keys=[resource_id])
    estimated_kiln = relationship('Resource', foreign_keys=[estimated_kiln_id])
    recipe = relationship('Recipe', foreign_keys=[recipe_id])
    size_ref = relationship('Size', foreign_keys=[size_id])


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    type = Column(PgEnum(TaskType), nullable=False)
    status = Column(PgEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    assigned_role = Column(PgEnum(UserRole))
    related_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='SET NULL'))
    related_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id', ondelete='SET NULL'))
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
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'))
    type = Column(PgEnum(TransactionType), nullable=False)
    quantity = Column(sa.Numeric(12, 3), nullable=False)
    related_order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id', ondelete='SET NULL'))
    related_position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id', ondelete='SET NULL'))
    reason = Column(PgEnum(WriteOffReason))
    notes = Column(sa.Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    # Receiving approval fields
    defect_percent = Column(sa.Numeric(5, 2), nullable=True)
    quality_notes = Column(sa.Text, nullable=True)
    approval_status = Column(sa.String(20), nullable=True)  # 'pending', 'approved', 'rejected', 'partial'
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(sa.DateTime(timezone=True), nullable=True)
    accepted_quantity = Column(sa.Numeric(12, 3), nullable=True)

    material = relationship('Material', foreign_keys=[material_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    related_order = relationship('ProductionOrder', foreign_keys=[related_order_id])
    related_position = relationship('OrderPosition', foreign_keys=[related_position_id])
    created_by_rel = relationship('User', foreign_keys=[created_by])
    approved_by_rel = relationship('User', foreign_keys=[approved_by])


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


class QualityChecklist(Base):
    """Structured QC checklists for pre-kiln and final inspections."""
    __tablename__ = 'quality_checklists'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    check_type = Column(sa.String(30), nullable=False)  # 'pre_kiln' | 'final'
    checklist_results = Column(JSONB, nullable=False)  # {item_key: "pass"|"fail"|"na"}
    overall_result = Column(sa.String(20), nullable=False)  # 'pass' | 'fail' | 'needs_rework'
    checked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    position = relationship('OrderPosition', foreign_keys=[position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    checked_by_rel = relationship('User', foreign_keys=[checked_by])


class ProblemCard(Base):
    __tablename__ = 'problem_cards'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    location = Column(sa.String(200))
    description = Column(sa.Text, nullable=False)
    actions = Column(sa.Text)
    status = Column(sa.String(50), nullable=False, default='open')
    mode = Column(PgEnum(ProblemCardMode), nullable=True, default=ProblemCardMode.SIMPLE)
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
    date = Column(sa.Date, nullable=False, server_default=sa.text('CURRENT_DATE'))
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
    decided_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    decided_at = Column(sa.DateTime(timezone=True))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    source_order = relationship('ProductionOrder', foreign_keys=[source_order_id])
    source_position = relationship('OrderPosition', foreign_keys=[source_position_id])
    decided_by_user = relationship('User', foreign_keys=[decided_by])


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


class ManaShipment(Base):
    __tablename__ = 'mana_shipments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    items_json = Column(JSONB, nullable=False)
    status = Column(PgEnum(ManaShipmentStatus), nullable=False, default=ManaShipmentStatus.PENDING)
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
    typology_id = Column(UUID(as_uuid=True), ForeignKey('kiln_loading_typologies.id', ondelete='SET NULL'), nullable=True)
    status = Column(PgEnum(TpsStatus), nullable=False, default=TpsStatus.NORMAL)
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'shift', 'date', 'stage'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    typology = relationship('KilnLoadingTypology', foreign_keys=[typology_id])


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
    """Production operation with productivity norms.

    Examples:
    - Glazing (spray): 1 person → 3 sqm/hour
    - Glazing (brush): 1 person → 2 liters/hour
    - Cutting: 1 person → 50 pieces/hour
    - Packing: 1 person → 30 pieces/hour
    """
    __tablename__ = 'process_steps'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    norm_time_minutes = Column(sa.Numeric(8, 2), nullable=False)
    sequence = Column(sa.Integer, nullable=False)
    # Productivity norms
    productivity_rate = Column(sa.Numeric(10, 2), nullable=True)   # e.g. 3.0
    productivity_unit = Column(sa.String(50), nullable=True)       # e.g. "sqm/hour", "pcs/hour", "liters/hour"
    measurement_basis = Column(sa.String(50), nullable=True)       # "per_person", "per_machine", "per_shift"
    is_active = Column(sa.Boolean, nullable=False, server_default=sa.text('true'))
    notes = Column(sa.Text, nullable=True)
    # TPS Dashboard fields
    stage = Column(sa.String(100), nullable=True)                  # links to production_stage (glazing, sorting, etc.)
    shift_count = Column(sa.Integer, nullable=False, server_default=sa.text('2'))  # 1 or 2 shifts/day
    applicable_collections = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))  # e.g. ["raku","gold"]
    applicable_methods = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))      # e.g. ["ss","bs"]
    applicable_product_types = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))  # e.g. ["tile"]
    # AI auto-calibration (enabled by default — EMA α=0.3 + 15% threshold + 7 min points = safe)
    auto_calibrate = Column(sa.Boolean, nullable=False, server_default=sa.text('true'))
    calibration_ema = Column(sa.Numeric(10, 2), nullable=True)
    last_calibrated_at = Column(sa.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('factory_id', 'sequence'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    standard_works = relationship('StandardWork', back_populates='process_step', cascade='all, delete-orphan')


class StandardWork(Base):
    """Detailed sub-operations within a ProcessStep.

    Example for "Glazing (spray)":
    - Prepare glaze mixture: 15 min (setup)
    - Set up spray equipment: 10 min (setup)
    - Apply coats: per ProcessStep rate (productive)
    - Clean equipment: 20 min (setup)
    """
    __tablename__ = 'standard_work'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_step_id = Column(UUID(as_uuid=True), ForeignKey('process_steps.id', ondelete='CASCADE'), nullable=False)
    description = Column(sa.Text, nullable=False)
    time_minutes = Column(sa.Numeric(8, 2), nullable=False)
    is_setup = Column(sa.Boolean, nullable=False, server_default=sa.text('false'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    process_step = relationship('ProcessStep', back_populates='standard_works', foreign_keys=[process_step_id])


class CalibrationLog(Base):
    """Log of AI auto-calibration events for ProcessStep productivity rates."""
    __tablename__ = 'calibration_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    process_step_id = Column(UUID(as_uuid=True), ForeignKey('process_steps.id', ondelete='CASCADE'), nullable=False)
    previous_rate = Column(sa.Numeric(10, 2), nullable=False)
    new_rate = Column(sa.Numeric(10, 2), nullable=False)
    ema_value = Column(sa.Numeric(10, 2), nullable=True)
    data_points = Column(sa.Integer, nullable=False, default=0)
    trigger = Column(sa.String(50), nullable=False, default='manual')  # auto / manual / suggestion
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    process_step = relationship('ProcessStep', foreign_keys=[process_step_id])
    approver = relationship('User', foreign_keys=[approved_by])


class KilnLoadingTypology(Base):
    """Named kiln loading configuration that defines capacity by product characteristics."""
    __tablename__ = 'kiln_loading_typologies'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    name = Column(sa.String(200), nullable=False)
    # Matching criteria (JSONB arrays, empty = all)
    product_types = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    place_of_application = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    collections = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    methods = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    # Size range
    min_size_cm = Column(sa.Numeric(8, 2), nullable=True)
    max_size_cm = Column(sa.Numeric(8, 2), nullable=True)       # max long side
    max_short_side_cm = Column(sa.Numeric(8, 2), nullable=True)  # max short side
    # Loading preference
    preferred_loading = Column(sa.String(20), nullable=False, server_default=sa.text("'auto'"))
    # Temperature range
    min_firing_temp = Column(sa.Integer, nullable=True)
    max_firing_temp = Column(sa.Integer, nullable=True)
    # Shifts
    shift_count = Column(sa.Integer, nullable=False, server_default=sa.text('2'))
    # AI auto-calibration (enabled by default)
    auto_calibrate = Column(sa.Boolean, nullable=False, server_default=sa.text('true'))
    is_active = Column(sa.Boolean, nullable=False, server_default=sa.text('true'))
    priority = Column(sa.Integer, nullable=False, server_default=sa.text('0'))
    notes = Column(sa.Text, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    capacities = relationship('KilnTypologyCapacity', back_populates='typology', cascade='all, delete-orphan')


class KilnTypologyCapacity(Base):
    """Pre-computed capacity per kiln per typology."""
    __tablename__ = 'kiln_typology_capacities'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    typology_id = Column(UUID(as_uuid=True), ForeignKey('kiln_loading_typologies.id', ondelete='CASCADE'), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id', ondelete='CASCADE'), nullable=False)
    capacity_sqm = Column(sa.Numeric(10, 3), nullable=True)
    capacity_pcs = Column(sa.Integer, nullable=True)
    loading_method = Column(sa.String(20), nullable=True)
    num_levels = Column(sa.Integer, server_default=sa.text('1'))
    ref_size = Column(sa.String(20), nullable=True)
    ref_thickness_mm = Column(sa.Numeric(6, 2), server_default=sa.text('11'))
    ref_shape = Column(sa.String(20), server_default=sa.text("'rectangle'"))
    # AI correction
    ai_adjusted_sqm = Column(sa.Numeric(10, 3), nullable=True)
    calibration_ema = Column(sa.Numeric(10, 3), nullable=True)
    last_calibrated_at = Column(sa.DateTime(timezone=True), nullable=True)
    # Loading zone for mixed loading (edge/flat/filler/primary)
    zone = Column(sa.String(20), nullable=False, server_default=sa.text("'primary'"))
    # Metadata
    calculated_at = Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    calculation_input = Column(JSONB, nullable=True)
    calculation_output = Column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint('typology_id', 'resource_id', 'zone'),
    )

    typology = relationship('KilnLoadingTypology', back_populates='capacities', foreign_keys=[typology_id])
    resource = relationship('Resource', foreign_keys=[resource_id])


class StageTypologySpeed(Base):
    """Production speed per (stage x typology) combination.

    Allows configuring different processing speeds depending on what product
    typology is being processed at each production stage.
    """
    __tablename__ = 'stage_typology_speeds'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    typology_id = Column(UUID(as_uuid=True), ForeignKey('kiln_loading_typologies.id', ondelete='CASCADE'), nullable=False)
    stage = Column(sa.String(100), nullable=False)  # glazing, sorting, firing, etc.

    productivity_rate = Column(sa.Numeric(10, 2), nullable=False)  # e.g. 50.0
    rate_unit = Column(sa.String(20), nullable=False, server_default=sa.text("'pcs'"))  # 'pcs' or 'sqm'
    rate_basis = Column(sa.String(20), nullable=False, server_default=sa.text("'per_person'"))  # 'per_person' or 'per_brigade'
    time_unit = Column(sa.String(20), nullable=False, server_default=sa.text("'hour'"))  # 'min', 'hour', 'shift'

    shift_count = Column(sa.Integer, server_default=sa.text('2'))
    shift_duration_hours = Column(sa.Numeric(4, 1), server_default=sa.text('8.0'))
    brigade_size = Column(sa.Integer, server_default=sa.text('1'))  # people per brigade

    # Auto-calibration enabled by default — EMA α=0.3 smooths noise, 15% threshold
    # catches only persistent drift over ~2 weeks (min 7 data points).
    # Фактическая выработка учитывается с учётом типологий: YES —
    # calibrate_typology_speeds() filters TpsShiftMetric by typology_id.
    auto_calibrate = Column(sa.Boolean, server_default=sa.text('true'))
    calibration_ema = Column(sa.Numeric(10, 2), nullable=True)
    last_calibrated_at = Column(sa.DateTime(timezone=True), nullable=True)
    notes = Column(sa.Text, nullable=True)

    created_at = Column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    __table_args__ = (
        UniqueConstraint('typology_id', 'stage', name='uq_stage_typology_speed'),
    )

    typology = relationship('KilnLoadingTypology', backref='stage_speeds')
    factory = relationship('Factory', foreign_keys=[factory_id])


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
    """Scheduled maintenance entries for kilns. PM creates these."""
    __tablename__ = 'kiln_maintenance_schedule'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    maintenance_type = Column(sa.String(200), nullable=False)
    maintenance_type_id = Column(UUID(as_uuid=True), ForeignKey('kiln_maintenance_types.id'))
    scheduled_date = Column(sa.Date, nullable=False)
    scheduled_time = Column(sa.Time)                           # optional specific time
    estimated_duration_hours = Column(sa.Numeric(8, 2))        # how long it will take
    status = Column(PgEnum(MaintenanceStatus), nullable=False, default=MaintenanceStatus.PLANNED)
    notes = Column(sa.Text)
    completed_at = Column(sa.DateTime(timezone=True))
    completed_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'))
    is_recurring = Column(sa.Boolean, nullable=False, default=False)
    recurrence_interval_days = Column(sa.Integer)               # how often to repeat
    requires_empty_kiln = Column(sa.Boolean, nullable=False, default=False)
    requires_cooled_kiln = Column(sa.Boolean, nullable=False, default=False)
    requires_power_off = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    resource = relationship('Resource', foreign_keys=[resource_id])
    maintenance_type_rel = relationship('KilnMaintenanceType', foreign_keys=[maintenance_type_id])
    completed_by = relationship('User', foreign_keys=[completed_by_id])
    created_by_rel = relationship('User', foreign_keys=[created_by])
    factory = relationship('Factory', foreign_keys=[factory_id])


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


class KilnInspectionItem(Base):
    """Template items for kiln inspection checklists.
    Seeded once; shared across all kilns. Categories match the physical checklist."""
    __tablename__ = 'kiln_inspection_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(sa.String(100), nullable=False)  # e.g. "Frame & Stability"
    item_text = Column(sa.String(500), nullable=False)  # e.g. "Kiln stands stable, no wobble"
    sort_order = Column(sa.Integer, nullable=False, default=0)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    applies_to_kiln_types = Column(JSONB)  # null = all; ["big","raku"] = specific types only


class KilnInspection(Base):
    """A single inspection session (one date × one kiln)."""
    __tablename__ = 'kiln_inspections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    inspection_date = Column(sa.Date, nullable=False)
    inspected_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('resource_id', 'inspection_date', name='uq_kiln_inspection_date'),
    )

    resource = relationship('Resource', foreign_keys=[resource_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    inspected_by = relationship('User', foreign_keys=[inspected_by_id])
    results = relationship('KilnInspectionResult', back_populates='inspection', cascade='all, delete-orphan')


class KilnInspectionResult(Base):
    """Result for a single checklist item within an inspection."""
    __tablename__ = 'kiln_inspection_results'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey('kiln_inspections.id', ondelete='CASCADE'), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey('kiln_inspection_items.id'), nullable=False)
    result = Column(sa.String(20), nullable=False)  # 'ok', 'not_applicable', 'damaged', 'needs_repair'
    notes = Column(sa.Text)

    inspection = relationship('KilnInspection', foreign_keys=[inspection_id], back_populates='results')
    item = relationship('KilnInspectionItem', foreign_keys=[item_id])


class KilnRepairLog(Base):
    """Repair log for kiln issues — tracks from report to completion."""
    __tablename__ = 'kiln_repair_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    date_reported = Column(sa.Date, nullable=False, server_default=sa.func.current_date())
    reported_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    issue_description = Column(sa.Text, nullable=False)
    diagnosis = Column(sa.Text)
    repair_actions = Column(sa.Text)
    spare_parts_used = Column(sa.Text)
    technician = Column(sa.String(200))
    date_completed = Column(sa.Date)
    status = Column(sa.String(30), nullable=False, default='open')  # open, in_progress, done
    notes = Column(sa.Text)
    # Link to inspection result that triggered this repair (optional)
    inspection_result_id = Column(UUID(as_uuid=True), ForeignKey('kiln_inspection_results.id'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    resource = relationship('Resource', foreign_keys=[resource_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    reported_by = relationship('User', foreign_keys=[reported_by_id])


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


class AuditLog(Base):
    """Audit trail for all database mutations (INSERT, UPDATE, DELETE).

    Populated automatically by the SQLAlchemy event-based audit system
    (api/audit.py) and also by the legacy log_delete() calls.
    """
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(sa.String(20), nullable=False)  # INSERT, UPDATE, DELETE, DEACTIVATE
    table_name = Column(sa.String(100), nullable=False)
    record_id = Column(UUID(as_uuid=True), nullable=False)
    old_data = Column(JSONB, nullable=True)  # snapshot before change (update/delete)
    new_data = Column(JSONB, nullable=True)  # snapshot after change (insert/update)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    user_email = Column(sa.String(255), nullable=True)
    ip_address = Column(sa.String(45), nullable=True)
    request_path = Column(sa.String(255), nullable=True)  # API endpoint that triggered the change
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


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
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id', ondelete='SET NULL'))
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id', ondelete='SET NULL'))
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


class KilnShelf(Base):
    """Kiln shelf (fire-resistant platform) with lifecycle tracking."""
    __tablename__ = 'kiln_shelves'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('resources.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    name = Column(sa.String(200), nullable=False)
    length_cm = Column(sa.Numeric(8, 2), nullable=False)
    width_cm = Column(sa.Numeric(8, 2), nullable=False)
    thickness_mm = Column(sa.Numeric(6, 2), nullable=False, default=15)
    material = Column(sa.String(100), default='silicon_carbide')
    # area_sqm is GENERATED ALWAYS in DB — read-only
    status = Column(sa.String(30), nullable=False, default='active')
    condition_notes = Column(sa.Text)
    write_off_reason = Column(sa.Text)
    write_off_photo_url = Column(sa.String(500))
    written_off_at = Column(sa.DateTime(timezone=True))
    written_off_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    purchase_date = Column(sa.Date)
    purchase_cost = Column(sa.Numeric(10, 2))
    firing_cycles_count = Column(sa.Integer, default=0)
    max_firing_cycles = Column(sa.Integer)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    kiln = relationship('Resource', foreign_keys=[resource_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    written_off_by_user = relationship('User', foreign_keys=[written_off_by])


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
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=True)
    code = Column(sa.String(50), nullable=False)
    name = Column(sa.String(200), nullable=False)
    description = Column(sa.Text)
    managed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    warehouse_type = Column(sa.String(50), nullable=False, default='section')
    display_order = Column(sa.Integer, nullable=False, default=0)
    is_default = Column(sa.Boolean, nullable=False, default=False)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'code'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    manager = relationship('User', foreign_keys=[managed_by])


class InventoryReconciliation(Base):
    __tablename__ = 'inventory_reconciliations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey('warehouse_sections.id'))
    status = Column(PgEnum(ReconciliationStatus), nullable=False, default=ReconciliationStatus.IN_PROGRESS)
    started_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    completed_at = Column(sa.DateTime(timezone=True))
    notes = Column(sa.Text)
    staff_count = Column(sa.Integer, nullable=True)
    scheduled_date = Column(sa.Date, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(sa.DateTime(timezone=True), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    section = relationship('WarehouseSection', foreign_keys=[section_id])
    started_by_rel = relationship('User', foreign_keys=[started_by])
    approved_by_rel = relationship('User', foreign_keys=[approved_by])


class InventoryReconciliationItem(Base):
    __tablename__ = 'inventory_reconciliation_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(UUID(as_uuid=True), ForeignKey('inventory_reconciliations.id', ondelete='CASCADE'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    system_quantity = Column(sa.Numeric(12, 3), nullable=False)
    actual_quantity = Column(sa.Numeric(12, 3), nullable=False)
    difference = Column(sa.Numeric(12, 3), nullable=False)
    adjustment_applied = Column(sa.Boolean, nullable=False, default=False)
    reason = Column(sa.String(50), nullable=True)  # 'natural_losses', 'formula_inaccuracy', 'counting_error', 'theft_damage', 'other'
    explanation = Column(sa.Text, nullable=True)
    explained_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    explained_at = Column(sa.DateTime(timezone=True), nullable=True)

    reconciliation = relationship('InventoryReconciliation', foreign_keys=[reconciliation_id])
    material = relationship('Material', foreign_keys=[material_id])
    explained_by_rel = relationship('User', foreign_keys=[explained_by])


# ── Packaging ──────────────────────────────────────────────


class PackagingBoxType(Base):
    """Box type card — links a packaging material to size capacities."""
    __tablename__ = 'packaging_box_types'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id', ondelete='CASCADE'), nullable=False)
    name = Column(sa.String(200), nullable=False)
    notes = Column(sa.Text)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    material = relationship('Material', foreign_keys=[material_id])
    capacities = relationship('PackagingBoxCapacity', back_populates='box_type', cascade='all, delete-orphan')
    spacer_rules = relationship('PackagingSpacerRule', back_populates='box_type', cascade='all, delete-orphan')


class PackagingBoxCapacity(Base):
    """How many tiles of a given size fit into a box type."""
    __tablename__ = 'packaging_box_capacities'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    box_type_id = Column(UUID(as_uuid=True), ForeignKey('packaging_box_types.id', ondelete='CASCADE'), nullable=False)
    size_id = Column(UUID(as_uuid=True), ForeignKey('sizes.id', ondelete='CASCADE'), nullable=False)
    pieces_per_box = Column(sa.Integer)
    sqm_per_box = Column(sa.Numeric(10, 4))

    __table_args__ = (
        UniqueConstraint('box_type_id', 'size_id'),
    )

    box_type = relationship('PackagingBoxType', foreign_keys=[box_type_id], back_populates='capacities')
    size = relationship('Size', foreign_keys=[size_id])


class PackagingSpacerRule(Base):
    """How many spacers of a given material are needed per box for a tile size."""
    __tablename__ = 'packaging_spacer_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    box_type_id = Column(UUID(as_uuid=True), ForeignKey('packaging_box_types.id', ondelete='CASCADE'), nullable=False)
    size_id = Column(UUID(as_uuid=True), ForeignKey('sizes.id', ondelete='CASCADE'), nullable=False)
    spacer_material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id', ondelete='CASCADE'), nullable=False)
    qty_per_box = Column(sa.Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint('box_type_id', 'size_id', 'spacer_material_id'),
    )

    box_type = relationship('PackagingBoxType', foreign_keys=[box_type_id], back_populates='spacer_rules')
    size = relationship('Size', foreign_keys=[size_id])
    spacer_material = relationship('Material', foreign_keys=[spacer_material_id])


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


class FiringProfile(Base):
    """Universal firing profile — temperature curve definition (not per-kiln)."""
    __tablename__ = 'firing_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)
    temperature_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('firing_temperature_groups.id', ondelete='SET NULL'),
        nullable=True,
    )
    typology_id = Column(
        UUID(as_uuid=True),
        ForeignKey('kiln_loading_typologies.id', ondelete='SET NULL'),
        nullable=True,
    )  # Layer 3: ramp/hold/cool curve depends on product typology
    product_type = Column(PgEnum(ProductType))                       # nullable = matches all
    collection = Column(sa.String(100))                              # nullable = matches all
    thickness_min_mm = Column(sa.Numeric(8, 2))                      # nullable = no lower bound
    thickness_max_mm = Column(sa.Numeric(8, 2))                      # nullable = no upper bound
    target_temperature = Column(sa.Integer, nullable=False)          # max firing temp °C
    total_duration_hours = Column(sa.Numeric(8, 2), nullable=False)  # total cycle time
    stages = Column(JSONB, nullable=False, default=list)             # temperature curve stages
    match_priority = Column(sa.Integer, nullable=False, default=0)   # higher = more specific
    is_default = Column(sa.Boolean, nullable=False, default=False)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    temperature_group = relationship('FiringTemperatureGroup', foreign_keys=[temperature_group_id])
    typology = relationship('KilnLoadingTypology', foreign_keys=[typology_id])


class RecipeFiringStage(Base):
    """Multi-firing stage definition per recipe (Gold = 2 rows, regular = 0 rows)."""
    __tablename__ = 'recipe_firing_stages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    stage_number = Column(sa.Integer, nullable=False, default=1)
    firing_profile_id = Column(UUID(as_uuid=True), ForeignKey('firing_profiles.id'))
    requires_glazing_before = Column(sa.Boolean, nullable=False, default=True)
    description = Column(sa.String(200))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('recipe_id', 'stage_number'),
    )

    recipe = relationship('Recipe', foreign_keys=[recipe_id])
    firing_profile = relationship('FiringProfile', foreign_keys=[firing_profile_id])


# ─── Shape Consumption Coefficients ─────────────────────────

class ShapeConsumptionCoefficient(Base):
    """Coefficient for converting bounding-box area to actual glazeable surface
    per shape × product_type combination.
    E.g. round/tile = 0.785 (π/4), triangle/tile = 0.5, rectangle/sink = 1.5 (includes bowl).
    """
    __tablename__ = 'shape_consumption_coefficients'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shape = Column(sa.String(20), nullable=False)
    product_type = Column(sa.String(20), nullable=False, default='tile')
    coefficient = Column(sa.Numeric(5, 3), nullable=False, default=1.0)
    description = Column(sa.Text)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('shape', 'product_type', name='uq_shape_coeff_shape_ptype'),
    )


# ─── Consumption Adjustment (actual vs expected) ────────────

class ConsumptionAdjustment(Base):
    """Records variance between expected and actual material consumption.
    Created when glazing master reports actual usage differs from calculated.
    PM reviews and approves/rejects — approved adjustments update the coefficient.
    """
    __tablename__ = 'consumption_adjustments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=False)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    expected_qty = Column(sa.Numeric(12, 4), nullable=False)
    actual_qty = Column(sa.Numeric(12, 4), nullable=False)
    variance_pct = Column(sa.Numeric(7, 2))  # (actual - expected) / expected × 100
    shape = Column(sa.String(20))
    product_type = Column(sa.String(20))
    suggested_coefficient = Column(sa.Numeric(10, 4))
    status = Column(sa.String(20), nullable=False, default='pending')  # pending | approved | rejected
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(sa.DateTime(timezone=True))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    position = relationship('OrderPosition', foreign_keys=[position_id])
    material = relationship('Material', foreign_keys=[material_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


# ─── Backup Log ─────────────────────────────────────────────

class BackupLog(Base):
    """Tracks database backup execution and status."""
    __tablename__ = 'backup_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    completed_at = Column(sa.DateTime(timezone=True))
    status = Column(sa.String(20), nullable=False, default=BackupStatus.IN_PROGRESS.value)
    file_size_bytes = Column(sa.BigInteger)
    s3_key = Column(sa.String(500))
    error_message = Column(sa.Text)
    backup_type = Column(sa.String(20), nullable=False, default=BackupType.SCHEDULED.value)


# ─── Firing Temperature Groups ──────────────────────────────

class FiringTemperatureGroup(Base):
    """Named temperature group for batch formation (replaces ±50°C auto-grouping).
    PM can create additional groups beyond the 2 defaults.
    Includes equipment specifications: thermocouple, control cable, control device.
    """
    __tablename__ = 'firing_temperature_groups'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(100), nullable=False)           # e.g. "Low Temperature", "High Temperature"
    temperature = Column(sa.Integer, nullable=False)        # working temperature in °C, e.g. 1012
    min_temperature = Column(sa.Integer)                    # DEPRECATED — kept for migration compatibility
    max_temperature = Column(sa.Integer)                    # DEPRECATED — kept for migration compatibility
    description = Column(sa.Text)
    # Equipment specifications (DEPRECATED — equipment now lives on Resource/Kiln)
    thermocouple = Column(sa.String(50))       # "chinese" | "indonesia_manufacture"
    control_cable = Column(sa.String(50))      # "indonesia_manufacture"
    control_device = Column(sa.String(50))     # "oven" | "moonjar"
    is_active = Column(sa.Boolean, nullable=False, default=True)
    display_order = Column(sa.Integer, nullable=False, default=0)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    recipes = relationship(
        'FiringTemperatureGroupRecipe',
        back_populates='temperature_group',
        cascade='all, delete-orphan',
    )


class FiringTemperatureGroupRecipe(Base):
    """Join table linking temperature groups to recipes."""
    __tablename__ = 'firing_temperature_group_recipes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    temperature_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey('firing_temperature_groups.id', ondelete='CASCADE'),
        nullable=False,
    )
    recipe_id = Column(
        UUID(as_uuid=True),
        ForeignKey('recipes.id', ondelete='CASCADE'),
        nullable=False,
    )
    is_default = Column(sa.Boolean, nullable=False, default=False)  # default recipe for this group

    __table_args__ = (
        UniqueConstraint('temperature_group_id', 'recipe_id',
                         name='uq_temp_group_recipe'),
    )

    temperature_group = relationship('FiringTemperatureGroup', back_populates='recipes')
    recipe = relationship('Recipe', foreign_keys=[recipe_id])


# ─── Kiln Maintenance Types ────────────────────────────────

class KilnMaintenanceType(Base):
    """Types of kiln maintenance/inspection with their requirements."""
    __tablename__ = 'kiln_maintenance_types'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(sa.String(200), nullable=False)           # e.g. "Thermocouple calibration"
    description = Column(sa.Text)
    duration_hours = Column(sa.Numeric(8, 2), nullable=False, default=2)   # how long it takes
    requires_empty_kiln = Column(sa.Boolean, nullable=False, default=False)  # kiln must be empty
    requires_cooled_kiln = Column(sa.Boolean, nullable=False, default=False) # kiln must be cooled down
    requires_power_off = Column(sa.Boolean, nullable=False, default=False)   # kiln must be turned off
    default_interval_days = Column(sa.Integer)                # recommended interval between checks
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


# ─── Telegram Position Photos ────────────────────────────────

class PositionPhoto(Base):
    """Photos received via Telegram bot for production documentation."""
    __tablename__ = 'position_photos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=True)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    telegram_file_id = Column(sa.String(200), nullable=True)  # nullable for web uploads
    telegram_chat_id = Column(sa.BigInteger)
    uploaded_by_telegram_id = Column(sa.BigInteger)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id', ondelete='SET NULL'), nullable=True)
    photo_type = Column(sa.String(30))  # glazing, firing, defect, packing, other, delivery, scale, quality
    photo_url = Column(sa.String(2048), nullable=True)  # For web-uploaded photos
    caption = Column(sa.Text)
    analysis_result = Column(sa.JSON, nullable=True)  # Vision API result: OCR readings, confidence, issues
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    position = relationship('OrderPosition', foreign_keys=[position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    uploaded_by = relationship('User', foreign_keys=[uploaded_by_user_id])
    batch = relationship('Batch', foreign_keys=[batch_id])


class SystemSetting(Base):
    """Key-value store for system-wide settings (e.g. Telegram owner chat ID)."""
    __tablename__ = 'system_settings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(sa.String(100), nullable=False, unique=True)
    value = Column(sa.Text)
    updated_at = Column(sa.DateTime(timezone=True), server_default=sa.func.now())


class ConsumptionRule(Base):
    """
    Consumption calculation rules for glaze/engobe per product configuration.

    Defines HOW to calculate material consumption based on:
    - collection, size, shape, thickness, product_type, place_of_application
    - recipe_type (glaze/engobe)
    - application_method (spray/brush)

    The rule stores consumption_ml_per_sqm — milliliters per square meter
    for a given combination of parameters.

    When multiple rules match, the most specific one wins (more non-null fields = higher priority).
    """
    __tablename__ = 'consumption_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_number = Column(sa.Integer, nullable=False)
    name = Column(sa.String(200), nullable=False)
    description = Column(sa.Text)

    # Matching criteria (all nullable — null means "any")
    collection = Column(sa.String(100))          # e.g. "New Collection"
    color_collection = Column(sa.String(100))    # e.g. "Season 2025/2026"
    product_type = Column(sa.String(30))         # tile / countertop / sink / 3d
    size_id = Column(UUID(as_uuid=True), ForeignKey('sizes.id'))
    shape = Column(sa.String(20))                # rectangle / round / freeform / etc.
    thickness_mm_min = Column(sa.Numeric(8, 2))  # min thickness (inclusive)
    thickness_mm_max = Column(sa.Numeric(8, 2))  # max thickness (inclusive)
    place_of_application = Column(sa.String(50)) # face_only / face_and_sides / etc.
    recipe_type = Column(sa.String(20))          # glaze / engobe
    application_method = Column(sa.String(20))   # spray / brush

    # Output: how much material per m² (optional override — rates normally come from recipe)
    consumption_ml_per_sqm = Column(sa.Numeric(10, 2), nullable=True)
    # Number of coats (layers)
    coats = Column(sa.Integer, nullable=False, default=1)
    # Specific gravity override (if different from recipe default)
    specific_gravity_override = Column(sa.Numeric(8, 4))

    # Priority — higher number = higher priority when multiple rules match
    priority = Column(sa.Integer, nullable=False, default=0)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    notes = Column(sa.Text)

    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    size = relationship('Size', foreign_keys=[size_id])


class FactoryCalendar(Base):
    __tablename__ = 'factory_calendar'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    date = Column(sa.Date, nullable=False)
    is_working_day = Column(sa.Boolean, default=True, nullable=False)
    num_shifts = Column(sa.Integer, default=2, nullable=False)
    holiday_name = Column(sa.String(200), nullable=True)
    holiday_source = Column(sa.String(50), nullable=True)  # 'government', 'balinese', 'manual'
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(sa.DateTime(timezone=True), nullable=True)
    notes = Column(sa.Text, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    factory = relationship('Factory', foreign_keys=[factory_id])
    __table_args__ = (UniqueConstraint('factory_id', 'date'),)


class Operation(Base):
    __tablename__ = 'operations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    name = Column(sa.String(100), nullable=False)
    description = Column(sa.Text, nullable=True)
    default_time_minutes = Column(sa.Numeric(8, 2), nullable=True)
    is_active = Column(sa.Boolean, default=True)
    sort_order = Column(sa.Integer, default=0)
    created_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    factory = relationship('Factory', foreign_keys=[factory_id])


class MasterPermission(Base):
    __tablename__ = 'master_permissions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    operation_id = Column(UUID(as_uuid=True), ForeignKey('operations.id'), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    granted_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship('User', foreign_keys=[user_id])
    operation = relationship('Operation', foreign_keys=[operation_id])
    grantor = relationship('User', foreign_keys=[granted_by])
    __table_args__ = (UniqueConstraint('user_id', 'operation_id'),)


class OperationLog(Base):
    __tablename__ = 'operation_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    operation_id = Column(UUID(as_uuid=True), ForeignKey('operations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id', ondelete='SET NULL'), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id', ondelete='SET NULL'), nullable=True)
    shift_date = Column(sa.Date, nullable=False)
    shift_number = Column(sa.Integer, nullable=True)
    started_at = Column(sa.DateTime(timezone=True), nullable=True)
    completed_at = Column(sa.DateTime(timezone=True), nullable=True)
    duration_minutes = Column(sa.Numeric(8, 2), nullable=True)
    quantity_processed = Column(sa.Integer, nullable=True)
    defect_count = Column(sa.Integer, default=0)
    notes = Column(sa.Text, nullable=True)
    source = Column(sa.String(20), default='telegram')  # 'telegram', 'dashboard', 'auto'
    created_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EscalationRule(Base):
    __tablename__ = 'escalation_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    task_type = Column(sa.String(50), nullable=False)
    pm_timeout_hours = Column(sa.Numeric(6, 2), nullable=False)
    ceo_timeout_hours = Column(sa.Numeric(6, 2), nullable=False)
    owner_timeout_hours = Column(sa.Numeric(6, 2), nullable=False)
    night_level = Column(sa.Integer, default=1)  # 1=morning, 2=repeat, 3=call
    is_active = Column(sa.Boolean, default=True)

    factory = relationship('Factory', foreign_keys=[factory_id])
    __table_args__ = (UniqueConstraint('factory_id', 'task_type'),)


class ReceivingSetting(Base):
    __tablename__ = 'receiving_settings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False, unique=True)
    approval_mode = Column(sa.String(20), nullable=False, default='all')  # 'all' or 'auto'
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    factory = relationship('Factory', foreign_keys=[factory_id])


class MaterialDefectThreshold(Base):
    __tablename__ = 'material_defect_thresholds'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False, unique=True)
    max_defect_percent = Column(sa.Numeric(5, 2), nullable=False, default=3.0)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    material = relationship('Material', foreign_keys=[material_id])


class EdgeHeightRule(Base):
    __tablename__ = 'edge_height_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    thickness_mm_min = Column(sa.Numeric(6, 2), nullable=False)
    thickness_mm_max = Column(sa.Numeric(6, 2), nullable=False)
    max_edge_height_cm = Column(sa.Numeric(6, 2), nullable=False)
    is_tested = Column(sa.Boolean, default=False)
    notes = Column(sa.Text, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    factory = relationship('Factory', foreign_keys=[factory_id])


# ──────────────────────────────────────────────────────────────────
# Stone Reservation tables (previously raw SQL only)
# ──────────────────────────────────────────────────────────────────

class StoneDefectRate(Base):
    __tablename__ = 'stone_defect_rates'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=True)
    size_category = Column(sa.String(20), nullable=False)
    product_type = Column(sa.String(50), nullable=False)
    defect_pct = Column(sa.Numeric(5, 4), nullable=False)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    __table_args__ = (
        UniqueConstraint('factory_id', 'size_category', 'product_type'),
    )


class StoneReservation(Base):
    __tablename__ = 'stone_reservations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    size_category = Column(sa.String(20), nullable=False)
    product_type = Column(sa.String(50), nullable=False)
    reserved_qty = Column(sa.Integer, nullable=False)
    reserved_sqm = Column(sa.Numeric(10, 3), nullable=False)
    stone_defect_pct = Column(sa.Numeric(5, 4), nullable=False)
    status = Column(sa.String(20), nullable=False, server_default='active')
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    reconciled_at = Column(sa.DateTime(timezone=True), nullable=True)

    position = relationship('OrderPosition', foreign_keys=[position_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    adjustments = relationship('StoneReservationAdjustment', back_populates='reservation')


class StoneReservationAdjustment(Base):
    __tablename__ = 'stone_reservation_adjustments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('stone_reservations.id', ondelete='CASCADE'), nullable=False)
    type = Column(sa.String(20), nullable=False)
    qty_sqm = Column(sa.Numeric(10, 3), nullable=False)
    reason = Column(sa.Text, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    reservation = relationship('StoneReservation', back_populates='adjustments')
    user = relationship('User', foreign_keys=[created_by])


# ──────────────────────────────────────────────────────────────────
# Production Defects (defect coefficient system)
# ──────────────────────────────────────────────────────────────────

class ProductionDefect(Base):
    __tablename__ = 'production_defects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=True)
    glaze_type = Column(sa.String(50), nullable=True)
    product_type = Column(sa.String(50), nullable=True)
    total_quantity = Column(sa.Integer, nullable=False)
    defect_quantity = Column(sa.Integer, nullable=False)
    defect_pct = Column(sa.Numeric(5, 4), nullable=True)
    fired_at = Column(sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE"))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


# ──────────────────────────────────────────────────────────────────
# Service Lead Times (service blocking timing)
# ──────────────────────────────────────────────────────────────────

class ServiceLeadTime(Base):
    __tablename__ = 'service_lead_times'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    service_type = Column(sa.String(50), nullable=False)
    lead_time_days = Column(sa.Integer, nullable=False, server_default=sa.text("3"))
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    __table_args__ = (
        UniqueConstraint('factory_id', 'service_type'),
    )


class PurchaseConsolidationSetting(Base):
    __tablename__ = 'purchase_consolidation_settings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False, unique=True)
    consolidation_window_days = Column(sa.Integer, nullable=False, default=7)
    urgency_threshold_days = Column(sa.Integer, nullable=False, default=5)
    planning_horizon_days = Column(sa.Integer, nullable=False, default=30)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_at = Column(sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    factory = relationship('Factory', foreign_keys=[factory_id])


# ──────────────────────────────────────────────────────────────────
# Kiln Rotation Rules (glaze sequencing per factory/kiln)
# ──────────────────────────────────────────────────────────────────

class KilnRotationRule(Base):
    __tablename__ = 'kiln_rotation_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    kiln_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=True)  # NULL = factory-wide default
    rule_name = Column(sa.String(100), nullable=False)
    glaze_sequence = Column(JSONB, nullable=False)  # ordered array of glaze types
    cooldown_minutes = Column(sa.Integer, default=0)  # cooldown between incompatible glazes
    incompatible_pairs = Column(JSONB, default=[])  # pairs that cannot follow each other
    is_active = Column(sa.Boolean, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'kiln_id', 'rule_name'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    kiln = relationship('Resource', foreign_keys=[kiln_id])


class ApplicationMethod(Base):
    __tablename__ = 'application_methods'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(sa.String(20), unique=True, nullable=False)
    name = Column(sa.String(100), nullable=False)
    engobe_method = Column(sa.String(20))                  # 'spray', 'brush', NULL
    glaze_method = Column(sa.String(20), nullable=False)   # 'spray', 'brush', 'splash', 'spray_stencil', 'silk_screen'
    needs_engobe = Column(sa.Boolean, nullable=False, default=True)
    two_stage_firing = Column(sa.Boolean, nullable=False, default=False)
    special_kiln = Column(sa.String(20))                   # 'raku' or NULL
    consumption_group_engobe = Column(sa.String(20))       # 'spray', 'brush', NULL
    consumption_group_glaze = Column(sa.String(20), nullable=False)  # 'spray', 'brush', 'silk_screen', 'splash'
    blocking_task_type = Column(sa.String(50))             # 'stencil_order', 'silk_screen_order', NULL
    sort_order = Column(sa.Integer, nullable=False, default=0)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class ApplicationCollection(Base):
    __tablename__ = 'application_collections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(sa.String(30), unique=True, nullable=False)
    name = Column(sa.String(100), nullable=False)
    allowed_methods = Column(JSONB, nullable=False, default=[])   # ['ss', 's'] for Authentic
    any_method = Column(sa.Boolean, nullable=False, default=False)  # TRUE for Exclusive, TopTable, WashBasin
    no_base_colors = Column(sa.Boolean, nullable=False, default=False)  # TRUE for Exclusive
    no_base_sizes = Column(sa.Boolean, nullable=False, default=False)   # TRUE for Exclusive
    product_type_restriction = Column(sa.String(50))       # 'countertop', 'sink', NULL
    sort_order = Column(sa.Integer, nullable=False, default=0)
    is_active = Column(sa.Boolean, nullable=False, default=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


# ── HR Module ────────────────────────────────────────────────────────

class Employee(Base):
    __tablename__ = 'employees'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)

    # Personal
    full_name = Column(sa.String(200), nullable=False)
    short_name = Column(sa.String(50), nullable=True)  # Nickname / short name used daily
    position = Column(sa.String(100), nullable=False)  # e.g. "Glazer", "Kiln Operator", "Sorter"
    phone = Column(sa.String(50), nullable=True)
    email = Column(sa.String(255), nullable=True)
    birth_date = Column(sa.Date, nullable=True)
    has_own_bpjs = Column(sa.Boolean, nullable=False, server_default='false')  # Employee has personal BPJS

    # Employment
    hire_date = Column(sa.Date, nullable=True)
    is_active = Column(sa.Boolean, nullable=False, server_default='true')
    employment_type = Column(sa.String(50), nullable=False, server_default="'full_time'")  # full_time, part_time, contract
    department = Column(sa.String(50), nullable=False, server_default="'production'")  # production, sales, administration
    work_schedule = Column(sa.String(20), nullable=False, server_default="'six_day'")  # five_day (Mon-Fri), six_day (Mon-Sat)
    bpjs_mode = Column(sa.String(20), nullable=False, server_default="'company_pays'")  # company_pays (company pays BPJS) or reimburse (company reimburses employee)
    employment_category = Column(sa.String(20), nullable=False, server_default="'formal'")  # formal, contractor
    commission_rate = Column(sa.Numeric(5, 2), nullable=True)  # % commission for sales (e.g., 5.00 = 5%)
    pay_period = Column(sa.String(20), nullable=False, server_default="'calendar_month'")  # calendar_month | 25_to_24

    # Salary
    base_salary = Column(sa.Numeric(12, 2), nullable=False, server_default='0')  # Monthly base IDR

    # Allowances (monthly fixed amounts IDR)
    allowance_bike = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    allowance_housing = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    allowance_food = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    allowance_bpjs = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    allowance_other = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    allowance_other_note = Column(sa.String(200), nullable=True)

    # Timestamps
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())

    # Relationships
    factory = relationship('Factory', backref='employees')


class Attendance(Base):
    __tablename__ = 'attendance'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey('employees.id'), nullable=False)
    date = Column(sa.Date, nullable=False)
    status = Column(sa.String(20), nullable=False)  # present, absent, sick, leave, half_day
    hours_worked = Column(sa.Numeric(4, 1), nullable=True)  # NULL = full day; e.g. 5.0 = came late
    overtime_hours = Column(sa.Numeric(4, 1), nullable=False, server_default='0')
    notes = Column(sa.Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('employee_id', 'date', name='uq_attendance_employee_date'),
    )

    employee = relationship('Employee', backref='attendance_records')
    recorded_by_rel = relationship('User', foreign_keys=[recorded_by])


class Shipment(Base):
    __tablename__ = 'shipments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('production_orders.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)

    # Shipping details
    tracking_number = Column(sa.String(100), nullable=True)
    carrier = Column(sa.String(100), nullable=True)  # e.g., "JNE", "TIKI", "J&T", "Pickup"
    shipping_method = Column(sa.String(50), nullable=True)  # "courier", "pickup", "container"

    # Quantities
    total_pieces = Column(sa.Integer, nullable=False, server_default='0')
    total_boxes = Column(sa.Integer, nullable=True)
    total_weight_kg = Column(sa.Numeric(10, 2), nullable=True)

    # Status: prepared, shipped, in_transit, delivered, cancelled
    status = Column(sa.String(30), nullable=False, server_default="'prepared'")

    # Dates
    shipped_at = Column(sa.DateTime(timezone=True), nullable=True)
    estimated_delivery = Column(sa.Date, nullable=True)
    delivered_at = Column(sa.DateTime(timezone=True), nullable=True)

    # People
    shipped_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    received_by = Column(sa.String(200), nullable=True)  # client's receiver name

    # Documents
    delivery_note_url = Column(sa.String(500), nullable=True)  # photo of surat jalan

    notes = Column(sa.Text, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    order = relationship('ProductionOrder', backref='shipments')
    factory = relationship('Factory', foreign_keys=[factory_id])
    shipped_by_rel = relationship('User', foreign_keys=[shipped_by])


class ShipmentItem(Base):
    __tablename__ = 'shipment_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey('shipments.id', ondelete='CASCADE'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'), nullable=False)
    quantity_shipped = Column(sa.Integer, nullable=False)
    box_number = Column(sa.Integer, nullable=True)
    notes = Column(sa.Text, nullable=True)

    shipment = relationship('Shipment', backref='items')
    position = relationship('OrderPosition', foreign_keys=[position_id])


# ──────────────────────────────────────────────────────────────────
# Firing Logs — temperature data during kiln firing
# ──────────────────────────────────────────────────────────────────

class FiringLog(Base):
    """Log temperature data during kiln firing for a batch."""
    __tablename__ = 'firing_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('batches.id', ondelete='CASCADE'), nullable=False)
    kiln_id = Column(UUID(as_uuid=True), ForeignKey('resources.id'), nullable=False)

    # Temperature data
    started_at = Column(sa.DateTime(timezone=True), nullable=True)
    ended_at = Column(sa.DateTime(timezone=True), nullable=True)
    peak_temperature = Column(sa.Numeric(6, 1), nullable=True)   # °C
    target_temperature = Column(sa.Numeric(6, 1), nullable=True)

    # Manual temperature readings (workers record periodically)
    # Format: [{"time": "HH:MM", "temp": 850, "notes": "..."}, ...]
    temperature_readings = Column(JSONB, nullable=True)

    # Firing profile used
    firing_profile_id = Column(UUID(as_uuid=True), ForeignKey('firing_profiles.id', ondelete='SET NULL'), nullable=True)

    # Result
    result = Column(sa.String(30), nullable=True)  # success, partial_failure, abort
    notes = Column(sa.Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    batch = relationship('Batch', backref='firing_logs')
    kiln = relationship('Resource', foreign_keys=[kiln_id])
    firing_profile = relationship('FiringProfile', foreign_keys=[firing_profile_id])
    recorded_by_user = relationship('User', foreign_keys=[recorded_by])


# ──────────────────────────────────────────────────────────────────
# Gamification — Streaks & Daily Challenges
# ──────────────────────────────────────────────────────────────────

class UserStreak(Base):
    """Track PM streak metrics per user + factory."""
    __tablename__ = 'user_streaks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    streak_type = Column(sa.String(30), nullable=False)  # on_time_delivery, zero_defects, daily_login, batch_utilization
    current_streak = Column(sa.Integer, nullable=False, default=0)
    best_streak = Column(sa.Integer, nullable=False, default=0)
    last_activity_date = Column(sa.Date)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'factory_id', 'streak_type'),
    )

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class DailyChallenge(Base):
    """One challenge per factory per day (deterministic from date hash)."""
    __tablename__ = 'daily_challenges'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    challenge_date = Column(sa.Date, nullable=False)
    challenge_type = Column(sa.String(30), nullable=False)
    title = Column(sa.String(300), nullable=False)
    description = Column(sa.Text)
    target_value = Column(sa.Integer, nullable=False, default=1)
    actual_value = Column(sa.Integer, nullable=False, default=0)
    completed = Column(sa.Boolean, nullable=False, default=False)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('factory_id', 'challenge_date'),
    )


class MasterAchievement(Base):
    """Master achievement tracking -- gamification Phase 6."""
    __tablename__ = 'master_achievements'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    achievement_type = Column(sa.String(30), nullable=False)
    level = Column(sa.Integer, nullable=False, default=0)
    unlocked_at = Column(sa.DateTime(timezone=True))
    progress_current = Column(sa.Integer, nullable=False, default=0)
    progress_target = Column(sa.Integer, nullable=False, default=100)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'achievement_type'),
    )

    user = relationship('User', foreign_keys=[user_id])


class UserPoints(Base):
    """Yearly points accumulation per user + factory."""
    __tablename__ = 'user_points'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    points_total = Column(sa.Integer, nullable=False, default=0)
    points_this_month = Column(sa.Integer, nullable=False, default=0)
    points_this_week = Column(sa.Integer, nullable=False, default=0)
    year = Column(sa.Integer, nullable=False, default=2026)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'factory_id', 'year'),
    )

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class PointTransaction(Base):
    """Individual point award record (audit trail)."""
    __tablename__ = 'point_transactions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    points = Column(sa.Integer, nullable=False)
    reason = Column(sa.String(50), nullable=False)
    details = Column(JSONB)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id', ondelete='SET NULL'))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])


class RecipeVerification(Base):
    """Per-ingredient photo verification during recipe preparation."""
    __tablename__ = 'recipe_verifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id'), nullable=False)
    position_id = Column(UUID(as_uuid=True), ForeignKey('order_positions.id'))
    recipe_id = Column(UUID(as_uuid=True), ForeignKey('recipes.id'))
    material_id = Column(UUID(as_uuid=True), ForeignKey('materials.id'), nullable=False)
    target_grams = Column(sa.Numeric(10, 2), nullable=False)
    actual_grams = Column(sa.Numeric(10, 2))
    accuracy_pct = Column(sa.Numeric(5, 2))
    points_awarded = Column(sa.Integer, default=0)
    photo_url = Column(sa.Text)
    ai_reading = Column(sa.Text)
    verified_at = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    material = relationship('Material', foreign_keys=[material_id])
    recipe = relationship('Recipe', foreign_keys=[recipe_id])


class TranscriptionLog(Base):
    __tablename__ = 'transcription_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    telegram_user_id = Column(sa.BigInteger, nullable=True)
    telegram_chat_id = Column(sa.BigInteger, nullable=True)
    audio_duration_sec = Column(sa.Integer, nullable=True)
    transcribed_text = Column(sa.Text, nullable=True)
    ai_response_summary = Column(sa.String(500), nullable=True)
    language_detected = Column(sa.String(10), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])


# ────────────────────────────────────────────────────────────────
# Gamification Engine v2
# ────────────────────────────────────────────────────────────────

class SkillBadge(Base):
    """Learnable skill in the factory — workers earn certification."""
    __tablename__ = 'skill_badges'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    code = Column(sa.String(50), nullable=False)
    name = Column(sa.String(200), nullable=False)
    name_id = Column(sa.String(200), nullable=True)  # Indonesian
    category = Column(sa.String(50), nullable=False)  # production, specialized, quality, safety, leadership
    icon = Column(sa.String(10), nullable=True)
    description = Column(sa.Text, nullable=True)
    required_operations = Column(sa.Integer, nullable=False, server_default='50')
    required_zero_defect_pct = Column(sa.Numeric(5, 2), nullable=True, server_default='90')
    required_mentor_approval = Column(sa.Boolean, nullable=False, server_default='false')
    points_on_earn = Column(sa.Integer, nullable=False, server_default='100')
    operation_id = Column(UUID(as_uuid=True), ForeignKey('operations.id', ondelete='SET NULL'), nullable=True)
    is_active = Column(sa.Boolean, nullable=False, server_default='true')
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (UniqueConstraint('factory_id', 'code', name='uq_skill_badge_factory_code'),)
    factory = relationship('Factory', foreign_keys=[factory_id])
    operation = relationship('Operation', foreign_keys=[operation_id])


class UserSkill(Base):
    """Worker's progress toward a skill badge."""
    __tablename__ = 'user_skills'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    skill_badge_id = Column(UUID(as_uuid=True), ForeignKey('skill_badges.id', ondelete='CASCADE'), nullable=False)
    status = Column(sa.String(20), nullable=False, server_default='learning')
    operations_completed = Column(sa.Integer, nullable=False, server_default='0')
    defect_free_pct = Column(sa.Numeric(5, 2), nullable=False, server_default='0')
    certified_at = Column(sa.DateTime(timezone=True), nullable=True)
    certified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    started_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())

    __table_args__ = (UniqueConstraint('user_id', 'skill_badge_id', name='uq_user_skill'),)
    user = relationship('User', foreign_keys=[user_id])
    skill_badge = relationship('SkillBadge', foreign_keys=[skill_badge_id])
    certifier = relationship('User', foreign_keys=[certified_by])


class Competition(Base):
    """Time-bounded competition between individuals or teams."""
    __tablename__ = 'competitions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    title = Column(sa.String(300), nullable=False)
    title_id = Column(sa.String(300), nullable=True)
    competition_type = Column(sa.String(20), nullable=False)  # individual, team
    metric = Column(sa.String(50), nullable=False, server_default='combined')
    scoring_formula = Column(sa.String(20), nullable=False, server_default='combined')
    quality_weight = Column(sa.Numeric(3, 1), nullable=False, server_default='1.0')
    start_date = Column(sa.Date, nullable=False)
    end_date = Column(sa.Date, nullable=False)
    status = Column(sa.String(20), nullable=False, server_default='upcoming')
    season_tag = Column(sa.String(50), nullable=True)
    prize_description = Column(sa.Text, nullable=True)
    prize_budget_idr = Column(sa.Numeric(12, 2), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    proposed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    creator = relationship('User', foreign_keys=[created_by])


class CompetitionTeam(Base):
    """Team in a team competition."""
    __tablename__ = 'competition_teams'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competition_id = Column(UUID(as_uuid=True), ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False)
    name = Column(sa.String(200), nullable=False)
    team_type = Column(sa.String(30), nullable=False)
    filter_key = Column(sa.String(100), nullable=True)
    icon = Column(sa.String(10), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    competition = relationship('Competition', foreign_keys=[competition_id], backref='teams')


class CompetitionEntry(Base):
    """Score entry for a participant in a competition."""
    __tablename__ = 'competition_entries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competition_id = Column(UUID(as_uuid=True), ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey('competition_teams.id', ondelete='CASCADE'), nullable=True)
    throughput_score = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    quality_score = Column(sa.Numeric(5, 2), nullable=False, server_default='100')
    combined_score = Column(sa.Numeric(10, 2), nullable=False, server_default='0')
    bonus_points = Column(sa.Integer, nullable=False, server_default='0')
    rank = Column(sa.Integer, nullable=True)
    entries_count = Column(sa.Integer, nullable=False, server_default='0')
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())

    __table_args__ = (
        UniqueConstraint('competition_id', 'user_id', name='uq_comp_user'),
        UniqueConstraint('competition_id', 'team_id', name='uq_comp_team'),
    )
    competition = relationship('Competition', foreign_keys=[competition_id])
    user = relationship('User', foreign_keys=[user_id])
    team = relationship('CompetitionTeam', foreign_keys=[team_id])


class PrizeRecommendation(Base):
    """AI-generated prize recommendation."""
    __tablename__ = 'prize_recommendations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    period = Column(sa.String(20), nullable=False)
    period_label = Column(sa.String(50), nullable=False)
    prize_type = Column(sa.String(30), nullable=False)
    recipient_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    recipient_team_name = Column(sa.String(200), nullable=True)
    prize_title = Column(sa.String(300), nullable=False)
    prize_description = Column(sa.Text, nullable=True)
    estimated_cost_idr = Column(sa.Numeric(12, 2), nullable=False)
    productivity_gain_pct = Column(sa.Numeric(5, 2), nullable=True)
    roi_estimate = Column(sa.Numeric(8, 2), nullable=True)
    ai_reasoning = Column(sa.Text, nullable=True)
    status = Column(sa.String(20), nullable=False, server_default='suggested')
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = Column(sa.DateTime(timezone=True), nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    factory = relationship('Factory', foreign_keys=[factory_id])
    recipient = relationship('User', foreign_keys=[recipient_user_id])
    approver = relationship('User', foreign_keys=[approved_by])


class GamificationSeason(Base):
    """Monthly gamification season with reset and final standings."""
    __tablename__ = 'gamification_seasons'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    name = Column(sa.String(100), nullable=False)
    start_date = Column(sa.Date, nullable=False)
    end_date = Column(sa.Date, nullable=False)
    status = Column(sa.String(20), nullable=False, server_default='active')
    final_standings = Column(JSONB, nullable=True)
    prizes_awarded = Column(JSONB, nullable=True)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (UniqueConstraint('factory_id', 'start_date', name='uq_season_factory_start'),)
    factory = relationship('Factory', foreign_keys=[factory_id])


class WorkerStageSkill(Base):
    """Which production stages a worker is qualified to perform."""
    __tablename__ = 'worker_stage_skills'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    stage = Column(sa.String(50), nullable=False)
    proficiency = Column(sa.String(20), nullable=False, server_default='capable')  # trainee / capable / expert
    certified_at = Column(sa.Date)
    certified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    notes = Column(sa.Text)
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (UniqueConstraint('user_id', 'factory_id', 'stage', name='uq_worker_stage_skill'),)

    user = relationship('User', foreign_keys=[user_id])
    factory = relationship('Factory', foreign_keys=[factory_id])
    certifier = relationship('User', foreign_keys=[certified_by])


class ShiftDefinition(Base):
    """Shift templates for a factory (e.g. Morning 06:00-14:00, Afternoon 14:00-22:00)."""
    __tablename__ = 'shift_definitions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    name = Column(sa.String(50), nullable=False)
    name_id = Column(sa.String(50))  # Indonesian: "Shift Pagi", "Shift Siang"
    start_time = Column(sa.Time, nullable=False)
    end_time = Column(sa.Time, nullable=False)
    is_active = Column(sa.Boolean, nullable=False, server_default='true')
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (UniqueConstraint('factory_id', 'name', name='uq_shift_def_name'),)
    factory = relationship('Factory', foreign_keys=[factory_id])


class ShiftAssignment(Base):
    """Daily assignment of workers to shifts and stages."""
    __tablename__ = 'shift_assignments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    shift_definition_id = Column(UUID(as_uuid=True), ForeignKey('shift_definitions.id', ondelete='CASCADE'), nullable=False)
    date = Column(sa.Date, nullable=False)
    stage = Column(sa.String(50), nullable=False)
    is_lead = Column(sa.Boolean, nullable=False, server_default='false')
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    __table_args__ = (
        UniqueConstraint('user_id', 'date', 'shift_definition_id', name='uq_shift_assignment_user_date_shift'),
    )

    factory = relationship('Factory', foreign_keys=[factory_id])
    user = relationship('User', foreign_keys=[user_id])
    shift_definition = relationship('ShiftDefinition', foreign_keys=[shift_definition_id])
    assigner = relationship('User', foreign_keys=[assigned_by])


class SchedulerConfig(Base):
    """Per-factory scheduler configuration — configurable buffer days and auto-buffer."""
    __tablename__ = 'scheduler_configs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(UUID(as_uuid=True), ForeignKey('factories.id', ondelete='CASCADE'), nullable=False, unique=True)
    pre_kiln_buffer_days = Column(sa.Integer, nullable=False, default=1)
    post_kiln_buffer_days = Column(sa.Integer, nullable=False, default=1)
    auto_buffer = Column(sa.Boolean, nullable=False, default=False)
    auto_buffer_multiplier = Column(sa.Numeric(4, 2), nullable=False, default=1.5)
    updated_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    factory = relationship('Factory', foreign_keys=[factory_id])
    updater = relationship('User', foreign_keys=[updated_by])


class OnboardingProgress(Base):
    """Tracks onboarding completion per section per role with quiz scores."""
    __tablename__ = 'onboarding_progress'
    __table_args__ = (
        UniqueConstraint('user_id', 'section_id', 'role', name='uq_onboarding_user_section_role'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(sa.String(50), nullable=False)
    role = Column(sa.String(50), nullable=False, server_default='production_manager')
    completed = Column(sa.Boolean, nullable=False, default=False)
    quiz_score = Column(sa.Integer)  # percent 0-100
    quiz_attempts = Column(sa.Integer, nullable=False, default=0)
    xp_earned = Column(sa.Integer, nullable=False, default=0)
    completed_at = Column(sa.DateTime(timezone=True))
    created_at = Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    user = relationship('User', foreign_keys=[user_id])
